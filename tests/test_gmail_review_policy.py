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
        messages = [
            ("announcement-low", "announcement", 0.65, True),
            ("promotion-low", "promotional", 0.65, True),
            ("assessment-high", "assessment", 0.95, False),
            ("unknown", "other", 0.0, True),
        ]

        return {
            "total_messages": len(messages),
            "category_counts": {},
            "messages": [
                {
                    "id": message_id,
                    "subject": message_id,
                    "category": category,
                    "confidence": confidence,
                    "requires_body": requires_body,
                }
                for message_id, category, confidence, requires_body in messages
            ],
        }


class FakeContentReader:
    def __init__(self):
        self.calls = []

    def read_message(self, message_id, max_chars=50000):
        self.calls.append(message_id)
        return {
            "body": "Test email content",
            "format": "plain",
            "truncated": False,
        }


def check(condition, description):
    if not condition:
        raise AssertionError(description)
    print(f"PASS: {description}")


def main():
    reader = FakeContentReader()
    service = GmailAcademicProcessingService(
        classification_service=FakeClassificationService(),
        content_reader=reader,
    )

    report = service.process_recent_messages()
    messages = {m["id"]: m for m in report["messages"]}

    check(
        messages["announcement-low"]["review_required"],
        "Low-confidence announcement requires review",
    )
    check(
        messages["promotion-low"]["review_required"],
        "Low-confidence promotional classification requires review",
    )
    check(
        messages["assessment-high"]["review_required"] is False,
        "High-confidence assessment does not require classification review",
    )
    check(
        messages["unknown"]["review_required"],
        "Unclassified message requires review",
    )
    check(
        reader.calls == ["announcement-low", "assessment-high"],
        "Only recognised academic categories retrieve bodies",
    )

    print("\nAll review-policy regression tests passed.")


if __name__ == "__main__":
    main()
