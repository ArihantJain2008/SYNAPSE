import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from services.task_service import TaskService


class TestTaskService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.service = TaskService(str(self.db_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_task(self):
        task = self.service.create_task(
            title="Complete JDBC assignment",
            task_type="assignment",
            source="manual",
            priority=1,
            metadata={"subject": "Java"},
        )

        self.assertEqual(task["title"], "Complete JDBC assignment")
        self.assertEqual(task["status"], "detected")
        self.assertEqual(task["priority"], 1)
        self.assertEqual(task["metadata"]["subject"], "Java")

    def test_update_status(self):
        task = self.service.create_task(
            title="Prepare for Java exam",
            task_type="exam",
        )

        updated = self.service.update_status(
            task["task_id"],
            "in_progress",
        )

        self.assertEqual(updated["status"], "in_progress")

    def test_completion_is_not_submission_approval(self):
        task = self.service.create_task(
            title="Submit Python assignment",
            task_type="assignment",
        )

        self.service.update_status(task["task_id"], "completed")
        updated = self.service.get_task(task["task_id"])

        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["approval_status"], "not_required")

    def test_approval_tracking(self):
        task = self.service.create_task(
            title="Review assignment before submission",
            task_type="assignment",
        )

        updated = self.service.set_approval(
            task["task_id"],
            "pending",
        )

        self.assertEqual(updated["approval_status"], "pending")

        updated = self.service.set_approval(
            task["task_id"],
            "approved",
        )

        self.assertEqual(updated["approval_status"], "approved")

    def test_task_event_history(self):
        task = self.service.create_task(
            title="Study JDBC",
            task_type="other",
        )

        self.service.update_status(
            task["task_id"],
            "in_progress",
        )

        events = self.service.get_task_events(task["task_id"])
        event_types = [event["event_type"] for event in events]

        self.assertIn("task_created", event_types)
        self.assertIn("status_changed", event_types)

    def test_filter_tasks(self):
        self.service.create_task(
            title="Java assignment",
            task_type="assignment",
        )

        self.service.create_task(
            title="Java exam",
            task_type="exam",
        )

        assignments = self.service.list_tasks(
            task_type="assignment"
        )

        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0]["title"], "Java assignment")

    def test_invalid_priority(self):
        with self.assertRaises(ValueError):
            self.service.create_task(
                title="Invalid task",
                task_type="other",
                priority=9,
            )

    def test_invalid_status(self):
        task = self.service.create_task(
            title="Test task",
            task_type="other",
        )

        with self.assertRaises(ValueError):
            self.service.update_status(
                task["task_id"],
                "invalid_status",
            )


    def test_date_only_deadline_uses_end_of_day_ist(self):
        task = self.service.create_task(
            title="Submit assignment",
            task_type="assignment",
            deadline="2026-11-20",
        )

        self.assertTrue(task["deadline"].endswith("+05:30"))
        self.assertIn("23:59:59", task["deadline"])

    def test_naive_datetime_is_interpreted_as_ist(self):
        task = self.service.create_task(
            title="Prepare for exam",
            task_type="exam",
            deadline="2026-11-20T18:00:00",
        )

        self.assertTrue(task["deadline"].endswith("+05:30"))
        self.assertIn("18:00:00", task["deadline"])

    def test_overdue_deadline_detection(self):
        task = self.service.create_task(
            title="Past assignment",
            task_type="assignment",
            deadline="2026-11-10",
        )

        result = self.service.get_deadline_status(
            task["task_id"],
            now=datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result, "overdue")

    def test_due_soon_detection(self):
        task = self.service.create_task(
            title="Upcoming assignment",
            task_type="assignment",
            deadline="2026-11-17T12:00:00+05:30",
        )

        result = self.service.get_deadline_status(
            task["task_id"],
            now=datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result, "due_soon")

    def test_completed_task_is_not_overdue(self):
        task = self.service.create_task(
            title="Completed assignment",
            task_type="assignment",
            deadline="2026-11-10",
        )

        self.service.update_status(task["task_id"], "completed")

        result = self.service.get_deadline_status(
            task["task_id"],
            now=datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result, "completed")
        self.assertEqual(self.service.list_overdue_tasks(
            now=datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        ), [])

    def test_invalid_deadline_is_rejected(self):
        with self.assertRaises(ValueError):
            self.service.create_task(
                title="Invalid deadline",
                task_type="assignment",
                deadline="not-a-date",
            )

    def test_task_without_deadline(self):
        task = self.service.create_task(
            title="General study",
            task_type="other",
        )

        result = self.service.get_deadline_status(task["task_id"])

        self.assertEqual(result, "no_deadline")


    def test_exam_can_outrank_urgent_minor_assignment(self):
        minor = self.service.create_task(
            title="Minor assignment",
            task_type="assignment",
            priority=5,
            deadline="2026-11-17T12:00:00+05:30",
        )
        exam = self.service.create_task(
            title="Major exam",
            task_type="exam",
            priority=3,
            deadline="2026-11-23T12:00:00+05:30",
        )
        now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

        minor_score = self.service.get_task_priority(
            minor["task_id"], now=now
        )["score"]
        exam_score = self.service.get_task_priority(
            exam["task_id"], now=now
        )["score"]

        self.assertGreater(exam_score, minor_score)

    def test_manual_priority_can_raise_importance(self):
        task = self.service.create_task(
            title="Important general task",
            task_type="other",
            priority=1,
        )
        result = self.service.get_task_priority(task["task_id"])
        self.assertEqual(result["importance"], 5)

    def test_overdue_task_gets_maximum_urgency(self):
        task = self.service.create_task(
            title="Overdue assignment",
            task_type="assignment",
            deadline="2026-11-10",
        )
        result = self.service.get_task_priority(
            task["task_id"],
            now=datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result["urgency"], 5)
        self.assertEqual(result["deadline_status"], "overdue")

    def test_task_without_deadline_has_zero_urgency(self):
        task = self.service.create_task(
            title="General study",
            task_type="other",
        )
        result = self.service.get_task_priority(task["task_id"])
        self.assertEqual(result["urgency"], 0)
        self.assertEqual(result["score"], 60)

    def test_completed_task_has_zero_priority_score(self):
        task = self.service.create_task(
            title="Finished exam preparation",
            task_type="exam",
        )
        self.service.update_status(task["task_id"], "completed")
        result = self.service.get_task_priority(task["task_id"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["label"], "Completed")

    def test_prioritized_list_sorts_highest_score_first(self):
        self.service.create_task(
            title="General study",
            task_type="other",
            priority=5,
        )
        self.service.create_task(
            title="Major exam",
            task_type="exam",
            priority=1,
        )
        tasks = self.service.list_prioritized_tasks()
        scores = [
            task["priority_analysis"]["score"] for task in tasks
        ]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(tasks[0]["title"], "Major exam")



    def test_priority_analysis_explains_score(self):
        task = self.service.create_task(
            title="Prepare for Java exam",
            task_type="exam",
            deadline="2026-11-17T12:00:00+05:30",
        )
        now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

        result = self.service.get_task_priority(task["task_id"], now=now)

        self.assertIn("importance_reason", result)
        self.assertIn("urgency_reason", result)
        self.assertIn("reason", result)
        self.assertEqual(result["score_breakdown"]["importance_points"], 100)
        self.assertEqual(result["score_breakdown"]["urgency_points"], 32)
        self.assertIn("within 24 hours", result["urgency_reason"])

    def test_invalid_now_is_rejected_for_task_without_deadline(self):
        task = self.service.create_task(
            title="General study", task_type="other"
        )
        with self.assertRaises(ValueError):
            self.service.get_task_priority(task["task_id"], now="invalid")

    def test_invalid_now_is_rejected_for_completed_task(self):
        task = self.service.create_task(
            title="Completed exam", task_type="exam"
        )
        self.service.update_status(task["task_id"], "completed")
        with self.assertRaises(ValueError):
            self.service.get_task_priority(task["task_id"], now="invalid")

    def test_invalid_now_is_rejected_for_task_with_deadline(self):
        task = self.service.create_task(
            title="Upcoming assignment",
            task_type="assignment",
            deadline="2026-11-20T12:00:00+05:30",
        )
        with self.assertRaises(ValueError):
            self.service.get_task_priority(
                task["task_id"], now="not-a-datetime"
            )


if __name__ == "__main__":
    unittest.main()
