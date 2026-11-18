import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


class AcademicMemory:
    """Local SQLite storage, semantic retrieval, and source lifecycle management."""

    def __init__(self, db_path="data/academic_memory.db", dimensions=1024):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions

        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    embedding BLOB NOT NULL,
                    embedding_dimensions INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_source
                ON documents(source_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_source_id
                ON documents(source_id)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    indexed_at TEXT NOT NULL,
                    UNIQUE(source_type, file_path)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    UNIQUE(source_id, version)
                )
            """)

    @contextmanager
    def _connect(self):
        """Provide a SQLite connection with automatic commit, rollback and close."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        try:
            yield conn
            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    @staticmethod
    def _normalize_path(file_path):
        return str(Path(file_path).resolve())

    @staticmethod
    def _source_id(source_type, file_path):
        identity = f"{source_type}|{file_path.casefold()}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @staticmethod
    def get_file_hash(file_path):
        """Calculate SHA-256 of the original file."""
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"Source file not found: {path}")

        digest = hashlib.sha256()

        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)

        return digest.hexdigest()

    def get_source(self, source_type, file_path):
        """Return the registered source record, if it exists."""
        normalized_path = self._normalize_path(file_path)

        with self._connect() as conn:
            row = conn.execute("""
                SELECT *
                FROM sources
                WHERE source_type = ? AND file_path = ?
            """, (source_type, normalized_path)).fetchone()

        return dict(row) if row else None

    def replace_source_documents(
        self,
        file_path,
        source_type,
        chunks,
    ):
        """
        Atomically index or replace all chunks belonging to one source.

        Each chunk must contain:
            title: str
            content: str
            embedding: normalized vector
            metadata: optional dict
        """

        normalized_path = self._normalize_path(file_path)
        path = Path(normalized_path)

        if not path.is_file():
            raise FileNotFoundError(f"Source file not found: {path}")

        if not source_type or not source_type.strip():
            raise ValueError("source_type cannot be empty.")

        if not chunks:
            raise ValueError("Cannot index a source without chunks.")

        source_id = self._source_id(source_type, normalized_path)
        file_hash = self.get_file_hash(path)

        # Validate every chunk before modifying the database.
        prepared_chunks = []

        for index, chunk in enumerate(chunks):
            title = chunk.get("title")
            content = chunk.get("content")
            metadata = chunk.get("metadata") or {}

            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"Chunk {index} has an invalid title.")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"Chunk {index} has empty content.")

            if not isinstance(metadata, dict):
                raise ValueError(f"Chunk {index} metadata must be a dict.")

            vector = np.asarray(
                chunk["embedding"], dtype=np.float32
            ).reshape(-1)

            if vector.size != self.dimensions:
                raise ValueError(
                    f"Chunk {index}: expected {self.dimensions} "
                    f"embedding dimensions, got {vector.size}."
                )

            norm = np.linalg.norm(vector)

            if not np.isclose(norm, 1.0, atol=1e-4):
                raise ValueError(
                    f"Chunk {index} embedding must be L2-normalized."
                )

            chunk_metadata = dict(metadata)
            chunk_metadata.update({
                "source_path": normalized_path,
                "source_version_pending": True,
                "chunk_id": index,
            })

            prepared_chunks.append({
                "title": title,
                "content": content,
                "embedding": vector,
                "metadata": chunk_metadata,
            })

        indexed_at = datetime.now(timezone.utc).isoformat()

        # Start a write transaction only after all embeddings are validated.
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")

            existing = conn.execute("""
                SELECT *
                FROM sources
                WHERE source_id = ?
            """, (source_id,)).fetchone()

            current_count = conn.execute("""
                SELECT COUNT(*)
                FROM documents
                WHERE source_id = ?
            """, (source_id,)).fetchone()[0]

            if (
                existing
                and existing["file_hash"] == file_hash
                and current_count == len(prepared_chunks)
            ):
                return {
                    "status": "unchanged",
                    "source_id": source_id,
                    "version": existing["version"],
                    "chunks_processed": current_count,
                }

            version = existing["version"] + 1 if existing else 1

            # Insert or update source registry.
            conn.execute("""
                INSERT INTO sources (
                    source_id,
                    source_type,
                    file_path,
                    file_hash,
                    version,
                    indexed_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    file_hash = excluded.file_hash,
                    version = excluded.version,
                    indexed_at = excluded.indexed_at
            """, (
                source_id,
                source_type,
                normalized_path,
                file_hash,
                version,
                indexed_at,
            ))

            # Remove previous active chunks for this source.
            conn.execute("""
                DELETE FROM documents
                WHERE source_id = ?
            """, (source_id,))

            # Insert the complete new version.
            for index, chunk in enumerate(prepared_chunks):
                metadata = dict(chunk["metadata"])
                metadata.pop("source_version_pending", None)
                metadata["source_version"] = version

                # Include chunk index so identical text in separate
                # chunks does not collide with the unique content_hash.
                identity = (
                    f"{source_type}|{source_id}|{index}|{chunk['content']}"
                )

                content_hash = hashlib.sha256(
                    identity.encode("utf-8")
                ).hexdigest()

                conn.execute("""
                    INSERT INTO documents (
                        content_hash,
                        source_type,
                        source_id,
                        title,
                        content,
                        metadata,
                        embedding,
                        embedding_dimensions,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    content_hash,
                    source_type,
                    source_id,
                    chunk["title"],
                    chunk["content"],
                    json.dumps(metadata),
                    chunk["embedding"].tobytes(),
                    self.dimensions,
                    indexed_at,
                ))

            # Keep a historical record of each successful version.
            conn.execute("""
                INSERT INTO source_versions (
                    source_id,
                    version,
                    file_hash,
                    indexed_at,
                    chunk_count
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                source_id,
                version,
                file_hash,
                indexed_at,
                len(prepared_chunks),
            ))

            return {
                "status": "indexed" if version == 1 else "updated",
                "source_id": source_id,
                "version": version,
                "chunks_processed": len(prepared_chunks),
                "file_hash": file_hash,
            }

    def add_document(
        self,
        title,
        content,
        embedding,
        source_type="manual",
        source_id=None,
        metadata=None,
    ):
        if not content or not content.strip():
            raise ValueError("Document content cannot be empty.")

        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)

        if vector.size != self.dimensions:
            raise ValueError(
                f"Expected {self.dimensions} dimensions, got {vector.size}."
            )

        norm = np.linalg.norm(vector)

        if not np.isclose(norm, 1.0, atol=1e-4):
            raise ValueError("Embedding must be L2-normalized.")

        identity = f"{source_type}|{source_id or ''}|{content}"

        content_hash = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        created_at = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO documents (
                    content_hash,
                    source_type,
                    source_id,
                    title,
                    content,
                    metadata,
                    embedding,
                    embedding_dimensions,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                content_hash,
                source_type,
                source_id,
                title,
                content,
                json.dumps(metadata or {}),
                vector.tobytes(),
                self.dimensions,
                created_at,
            ))

            row = conn.execute(
                "SELECT id FROM documents WHERE content_hash = ?",
                (content_hash,)
            ).fetchone()

            return row["id"]

    def search(self, query_embedding, top_k=5, source_type=None):
        query = np.asarray(
            query_embedding, dtype=np.float32
        ).reshape(-1)

        if query.size != self.dimensions:
            raise ValueError("Query embedding dimension mismatch.")

        norm = np.linalg.norm(query)

        if not np.isclose(norm, 1.0, atol=1e-4):
            raise ValueError("Query embedding must be normalized.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        sql = "SELECT * FROM documents"
        params = []

        if source_type:
            sql += " WHERE source_type = ?"
            params.append(source_type)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        results = []

        for row in rows:
            if row["embedding_dimensions"] != self.dimensions:
                continue

            stored_vector = np.frombuffer(
                row["embedding"], dtype=np.float32
            )

            score = float(np.dot(query, stored_vector))

            results.append({
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "source_type": row["source_type"],
                "source_id": row["source_id"],
                "metadata": json.loads(row["metadata"]),
                "similarity": score,
                "created_at": row["created_at"],
            })

        results.sort(
            key=lambda item: item["similarity"],
            reverse=True
        )

        return results[:top_k]

    def count(self):
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM documents"
            ).fetchone()[0]
