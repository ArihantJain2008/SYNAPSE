
from pathlib import Path

from services.document_extractor import DocumentExtractor
from services.document_chunker import DocumentChunker
from services.embedding_service import EmbeddingService
from services.academic_memory import AcademicMemory


class IngestionService:
    """Local academic document ingestion with source lifecycle management."""

    def __init__(self):
        self.extractor = DocumentExtractor()
        self.embedder = EmbeddingService()

        self.chunker = DocumentChunker(
            tokenizer=self.embedder.tokenizer,
            max_tokens=110,
            overlap_tokens=20,
        )

        self.memory = AcademicMemory()

    def ingest(self, file_path, source_type="document"):
        path = Path(file_path).resolve()

        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        print(f"\nChecking: {path.name}")

        # Check whether this source has already been indexed.
        current_hash = self.memory.get_file_hash(path)
        existing_source = self.memory.get_source(source_type, path)

        if existing_source and existing_source["file_hash"] == current_hash:
            with self.memory._connect() as conn:
                active_count = conn.execute("""
                    SELECT COUNT(*)
                    FROM documents
                    WHERE source_id = ?
                """, (existing_source["source_id"],)).fetchone()[0]

            if active_count > 0:
                print("File unchanged. Skipping ingestion.")

                return {
                    "status": "unchanged",
                    "file_name": path.name,
                    "source_id": existing_source["source_id"],
                    "version": existing_source["version"],
                    "chunks_processed": active_count,
                    "total_memory_documents": self.memory.count(),
                }

        print("Reading:", path.name)

        extracted = self.extractor.extract(path)

        if extracted["needs_ocr"]:
            return {
                "status": "needs_ocr",
                "file_name": path.name,
                "message": "No extractable PDF text found. OCR is required.",
            }

        if extracted["extracted_characters"] == 0:
            return {
                "status": "empty",
                "file_name": path.name,
                "message": "The document contains no extractable text.",
            }

        print("Extracted characters:", extracted["extracted_characters"])

        chunks = self.chunker.chunk(extracted)

        if not chunks:
            return {
                "status": "empty",
                "file_name": path.name,
                "message": "No usable text chunks were generated.",
            }

        print("Generated chunks:", len(chunks))
        print("Generating embeddings...")

        prepared_chunks = []

        for chunk in chunks:
            embedding = self.embedder.embed_document(chunk["text"])

            prepared_chunks.append({
                "title": (
                    f"{path.stem} - Chunk {chunk['chunk_id'] + 1}"
                ),
                "content": chunk["text"],
                "embedding": embedding,
                "metadata": {
                    "file_name": path.name,
                    "file_path": str(path),
                    "file_type": extracted["file_type"],
                    "page": chunk["page"],
                    "chunk_id": chunk["chunk_id"],
                    "start_offset": chunk["start_offset"],
                    "end_offset": chunk["end_offset"],
                    "token_count": chunk["token_count"],
                },
            })

        # Detect modifications made while extraction or embedding ran.
        final_hash = self.memory.get_file_hash(path)

        if final_hash != current_hash:
            return {
                "status": "source_changed_during_ingestion",
                "file_name": path.name,
                "message": (
                    "The file changed during processing. "
                    "Run ingestion again to index its latest version."
                ),
            }

        print("Committing source version...")

        result = self.memory.replace_source_documents(
            file_path=path,
            source_type=source_type,
            chunks=prepared_chunks,
        )

        result.update({
            "file_name": path.name,
            "total_memory_documents": self.memory.count(),
        })

        print("Ingestion status:", result["status"])
        print("Indexed chunks:", result["chunks_processed"])
        print("Source version:", result["version"])

        return result
