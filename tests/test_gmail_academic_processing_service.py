import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gmail_academic_processing_service import (
    GmailAcademicProcessingService,
)


class FakeClassificationService:
    def classify_recent_messages(self, max_results=10):
        return {
            "total_messages": 4,
            "category_counts": {},
            "messages": [
                {"id": "assignment-1", "subject": "Assignment submission",
                 "category": "assignment", "confidence": 0.95,
                 "requires_body": False},
                {"id": "promotion-1", "subject": "Special offer",
                 "category": "promotional", "confidence": 0.80,
                 "requires_body": False},
                {"id": "unknown-1", "subject": "Unrecognised message",
                 "category": "other", "confidence": 0.0,
                 "requires_body": True},
                {"id": "assessment-1", "subject": "Exam results",
                 "category": "assessment", "confidence": 0.95,
                 "requires_body": False},
            ],
        }


class FakeContentReader:
    def __init__(self, fail_ids=None):
        self.calls = []
        self.fail_ids = set(fail_ids or [])

    def read_message(self, message_id, max_chars=50000):
        self.calls.append((message_id, max_chars))
        if message_id in self.fail_ids:
            raise RuntimeError("Simulated retrieval failure")
        return {
            "message_id": message_id,
            "body": f"Body for {message_id}",
            "format": "plain",
            "truncated": False,
            "original_length": 20,
            "parts_read": 1,
        }


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main():
    print("Testing Gmail academic processing service...\n")

    reader = FakeContentReader()
    service = GmailAcademicProcessingService(
        classification_service=FakeClassificationService(),
        content_reader=reader,
    )
    report = service.process_recent_messages(max_results=4)

    messages = {item["id"]: item for item in report["messages"]}

    check(report["total_messages"] == 4, "All messages are processed")
    check(
        [call[0] for call in reader.calls]
        == ["assignment-1", "assessment-1"],
        "Only academic categories have bodies retrieved",
    )
    check(
        messages["assignment-1"]["body"] == "Body for assignment-1",
        "Assignment body is retrieved",
    )
    check(
        messages["assessment-1"]["body_status"] == "retrieved",
        "High-confidence assessment body is retrieved",
    )
    check(
        messages["promotion-1"]["body_status"] == "skipped_promotional",
        "Promotional email is skipped",
    )
    check(
        messages["unknown-1"]["body_status"] == "skipped_uncategorized"
        and messages["unknown-1"]["review_required"],
        "Unclassified email is flagged for review",
    )

    failing_reader = FakeContentReader(fail_ids={"assignment-1"})
    failing_service = GmailAcademicProcessingService(
        classification_service=FakeClassificationService(),
        content_reader=failing_reader,
    )
    failed_report = failing_service.process_recent_messages(max_results=4)
    failed_messages = {
        item["id"]: item for item in failed_report["messages"]
    }

    check(
        failed_messages["assignment-1"]["body_status"] == "retrieval_failed",
        "Retrieval failure is recorded",
    )
    check(
        failed_messages["assessment-1"]["body_status"] == "retrieved",
        "A failure does not stop later messages",
    )
    check(
        failed_messages["assignment-1"]["retrieval_error"] == "RuntimeError",
        "Only the exception type is recorded",
    )

    print("\nAll Gmail academic processing tests passed.")


if __name__ == "__main__":
    main()
