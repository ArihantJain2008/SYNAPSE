import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path


INDIA_TZ = timezone(timedelta(hours=5, minutes=30), name="IST")


class TaskService:
    TASK_TYPES = {
        "assignment",
        "exam",
        "project",
        "message",
        "other",
    }

    STATUSES = {
        "detected",
        "needs_clarification",
        "ready",
        "in_progress",
        "awaiting_review",
        "completed",
        "dismissed",
    }

    APPROVAL_STATUSES = {
        "not_required",
        "pending",
        "approved",
        "rejected",
    }

    SOURCES = {
        "manual",
        "gmail",
        "google_classroom",
        "local_system",
    }

    def __init__(self, db_path="data/academic_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @contextmanager
    def _connect(self):
        """Manage SQLite connection, transaction, and cleanup."""
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

    def _initialize_database(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    task_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_id TEXT,
                    status TEXT NOT NULL DEFAULT 'detected',
                    approval_status TEXT NOT NULL DEFAULT 'not_required',
                    priority INTEGER NOT NULL DEFAULT 3,
                    deadline TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS task_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON tasks(status);

                CREATE INDEX IF NOT EXISTS idx_tasks_deadline
                ON tasks(deadline);

                CREATE INDEX IF NOT EXISTS idx_task_events_task
                ON task_events(task_id);
            """)

    @staticmethod
    def _normalize_deadline(value):
        """Normalize deadlines to timezone-aware Asia/Kolkata ISO strings."""
        if value is None:
            return None

        if not isinstance(value, str) or not value.strip():
            raise ValueError("Deadline must be a valid ISO date or datetime.")

        value = value.strip()

        try:
            if len(value) == 10:
                parsed_date = date.fromisoformat(value)
                parsed = datetime.combine(
                    parsed_date,
                    time.max,
                    tzinfo=INDIA_TZ,
                )
            else:
                parsed = datetime.fromisoformat(
                    value.replace("Z", "+00:00")
                )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=INDIA_TZ)

            return parsed.astimezone(INDIA_TZ).isoformat()

        except (ValueError, OverflowError) as exc:
            raise ValueError(
                "Invalid deadline. Use YYYY-MM-DD or ISO datetime."
            ) from exc

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def _record_event(
        self,
        conn,
        task_id,
        event_type,
        old_value=None,
        new_value=None,
        details="",
    ):
        conn.execute("""
            INSERT INTO task_events (
                task_id,
                event_type,
                old_value,
                new_value,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            event_type,
            old_value,
            new_value,
            details,
            self._now(),
        ))

    def create_task(
        self,
        title,
        task_type,
        source="manual",
        description="",
        deadline=None,
        priority=3,
        source_id=None,
        metadata=None,
    ):
        title = title.strip() if isinstance(title, str) else ""

        if not title:
            raise ValueError("Task title cannot be empty.")

        if task_type not in self.TASK_TYPES:
            raise ValueError(f"Invalid task type: {task_type}")

        if source not in self.SOURCES:
            raise ValueError(f"Invalid source: {source}")

        if not isinstance(priority, int) or not 1 <= priority <= 5:
            raise ValueError("Priority must be an integer from 1 to 5.")

        deadline = self._normalize_deadline(deadline)

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary.")

        task_id = str(uuid.uuid4())
        now = self._now()

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    task_id,
                    title,
                    description,
                    task_type,
                    source,
                    source_id,
                    status,
                    approval_status,
                    priority,
                    deadline,
                    created_at,
                    updated_at,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, 'detected',
                        'not_required', ?, ?, ?, ?, ?)
            """, (
                task_id,
                title,
                description,
                task_type,
                source,
                source_id,
                priority,
                deadline,
                now,
                now,
                json.dumps(metadata),
            ))

            self._record_event(
                conn,
                task_id,
                "task_created",
                new_value=title,
                details=f"Created from {source}",
            )

        return self.get_task(task_id)

    def get_task(self, task_id):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()

        return self._serialize_task(row) if row else None

    def list_tasks(self, status=None, task_type=None):
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status is not None:
            if status not in self.STATUSES:
                raise ValueError(f"Invalid status: {status}")
            query += " AND status = ?"
            params.append(status)

        if task_type is not None:
            if task_type not in self.TASK_TYPES:
                raise ValueError(f"Invalid task type: {task_type}")
            query += " AND task_type = ?"
            params.append(task_type)

        query += """
            ORDER BY
                CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
                deadline ASC,
                priority ASC,
                created_at DESC
        """

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [self._serialize_task(row) for row in rows]

    def update_status(self, task_id, new_status):
        if new_status not in self.STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        now = self._now()

        with self._connect() as conn:
            row = conn.execute(
                "SELECT status FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Task not found.")

            old_status = row["status"]

            if old_status == new_status:
                return self.get_task(task_id)

            completed_at = now if new_status == "completed" else None

            conn.execute("""
                UPDATE tasks
                SET status = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE task_id = ?
            """, (
                new_status,
                now,
                completed_at,
                task_id,
            ))

            self._record_event(
                conn,
                task_id,
                "status_changed",
                old_value=old_status,
                new_value=new_status,
            )

        return self.get_task(task_id)

    def set_approval(self, task_id, approval_status):
        if approval_status not in self.APPROVAL_STATUSES:
            raise ValueError(
                f"Invalid approval status: {approval_status}"
            )

        now = self._now()

        with self._connect() as conn:
            row = conn.execute(
                "SELECT approval_status FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()

            if row is None:
                raise ValueError("Task not found.")

            old_status = row["approval_status"]

            conn.execute("""
                UPDATE tasks
                SET approval_status = ?,
                    updated_at = ?
                WHERE task_id = ?
            """, (
                approval_status,
                now,
                task_id,
            ))

            self._record_event(
                conn,
                task_id,
                "approval_changed",
                old_value=old_status,
                new_value=approval_status,
            )

        return self.get_task(task_id)

    def get_deadline_status(self, task_id, now=None, due_soon_hours=48):
        """Return no_deadline, overdue, due_soon, upcoming, completed or dismissed."""
        task = self.get_task(task_id)

        if task is None:
            raise ValueError("Task not found.")

        if task["status"] in {"completed", "dismissed"}:
            return task["status"]

        if task["deadline"] is None:
            return "no_deadline"

        if not isinstance(due_soon_hours, (int, float)) or due_soon_hours < 0:
            raise ValueError("due_soon_hours must be a non-negative number.")

        if now is None:
            current = datetime.now(INDIA_TZ)
        elif isinstance(now, datetime):
            current = now
            if current.tzinfo is None:
                current = current.replace(tzinfo=INDIA_TZ)
            current = current.astimezone(INDIA_TZ)
        else:
            raise ValueError("now must be a datetime or None.")

        deadline = datetime.fromisoformat(task["deadline"])

        current_utc = current.astimezone(timezone.utc)
        deadline_utc = deadline.astimezone(timezone.utc)

        if deadline_utc < current_utc:
            return "overdue"

        if deadline_utc <= current_utc + timedelta(hours=due_soon_hours):
            return "due_soon"

        return "upcoming"

    def list_overdue_tasks(self, now=None):
        """Return unfinished tasks whose deadlines have passed."""
        if now is None:
            current = datetime.now(INDIA_TZ)
        elif isinstance(now, datetime):
            current = now
            if current.tzinfo is None:
                current = current.replace(tzinfo=INDIA_TZ)
            current = current.astimezone(INDIA_TZ)
        else:
            raise ValueError("now must be a datetime or None.")

        current_utc = current.astimezone(timezone.utc)

        tasks = self.list_tasks()
        overdue = []

        for task in tasks:
            if task["status"] in {"completed", "dismissed"}:
                continue

            if task["deadline"] is None:
                continue

            deadline = datetime.fromisoformat(task["deadline"])

            if deadline.astimezone(timezone.utc) < current_utc:
                overdue.append(task)

        return overdue

    @staticmethod
    def _normalize_now(now):
        """Validate and normalize an optional datetime to IST."""
        if now is None:
            return None
        if not isinstance(now, datetime):
            raise ValueError("now must be a datetime or None.")
        if now.tzinfo is None:
            now = now.replace(tzinfo=INDIA_TZ)
        return now.astimezone(INDIA_TZ)

    def get_task_priority(self, task_id, now=None):
        """Return a deterministic, explainable priority analysis."""
        current = self._normalize_now(now)

        task = self.get_task(task_id)
        if task is None:
            raise ValueError("Task not found.")

        importance_by_type = {
            "exam": 5,
            "project": 4,
            "assignment": 3,
            "message": 2,
            "other": 1,
        }

        base_importance = importance_by_type[task["task_type"]]
        manual_importance = 6 - task["priority"]
        importance = max(base_importance, manual_importance)

        if manual_importance > base_importance:
            importance_reason = (
                f"Manual priority {task['priority']} raises importance "
                f"from {base_importance} to {importance}."
            )
        else:
            importance_reason = (
                f"{task['task_type'].title()} tasks have base importance "
                f"{base_importance}; manual priority does not raise it."
            )

        if task["status"] in {"completed", "dismissed"}:
            urgency = 0
            deadline_status = task["status"]
            urgency_reason = (
                f"Task is {task['status']}; it receives no active urgency."
            )
            score = 0
            label = task["status"].title()
        else:
            deadline_status = self.get_deadline_status(
                task_id, now=current
            )

            if deadline_status == "no_deadline":
                urgency = 0
                urgency_reason = "No deadline is set."
            elif deadline_status == "overdue":
                urgency = 5
                urgency_reason = "The deadline has already passed."
            else:
                if current is None:
                    current = datetime.now(INDIA_TZ)

                deadline = datetime.fromisoformat(task["deadline"])
                remaining = (
                    deadline.astimezone(timezone.utc)
                    - current.astimezone(timezone.utc)
                )
                remaining_hours = remaining.total_seconds() / 3600

                if remaining_hours <= 24:
                    urgency = 4
                    urgency_reason = "The deadline is within 24 hours."
                elif remaining_hours <= 48:
                    urgency = 3
                    urgency_reason = "The deadline is within 48 hours."
                elif remaining_hours <= 168:
                    urgency = 2
                    urgency_reason = "The deadline is within 7 days."
                else:
                    urgency = 1
                    urgency_reason = "The deadline is more than 7 days away."

            score = importance * 20 + urgency * 8

            if score >= 120:
                label = "Critical"
            elif score >= 100:
                label = "High"
            elif score >= 70:
                label = "Medium"
            else:
                label = "Low"

        importance_points = importance * 20
        urgency_points = urgency * 8

        return {
            "task_id": task_id,
            "importance": importance,
            "importance_reason": importance_reason,
            "urgency": urgency,
            "urgency_reason": urgency_reason,
            "score": score,
            "score_breakdown": {
                "importance": importance,
                "importance_points": importance_points,
                "urgency": urgency,
                "urgency_points": urgency_points,
                "formula": "importance * 20 + urgency * 8",
            },
            "label": label,
            "deadline_status": deadline_status,
            "reason": f"{importance_reason} {urgency_reason}",
        }

    def list_prioritized_tasks(self, status=None, task_type=None, now=None):
        """Return tasks sorted by calculated priority, highest first."""
        tasks = self.list_tasks(status=status, task_type=task_type)

        for task in tasks:
            task["priority_analysis"] = self.get_task_priority(
                task["task_id"], now=now
            )

        tasks.sort(
            key=lambda task: (
                -task["priority_analysis"]["score"],
                task["deadline"] is None,
                task["deadline"] or "",
                task["created_at"],
            )
        )

        return tasks

    def get_task_events(self, task_id):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT *
                FROM task_events
                WHERE task_id = ?
                ORDER BY created_at ASC, event_id ASC
            """, (task_id,)).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def _serialize_task(row):
        if row is None:
            return None

        task = dict(row)
        task["metadata"] = json.loads(task["metadata"])
        return task
