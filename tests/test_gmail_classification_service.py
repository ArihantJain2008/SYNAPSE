import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gmail_classification_service import GmailClassificationService


class FakeGmailReader:
    def list_recent_messages(self, max_results=10):
        messages = [
            {
                "id": "msg001",
                "thread_id": "thread001",
                "sender": "professor@college.edu",
                "subject": "Assignment submission deadline",
                "date": "Mon, 16 Nov 2026 10:00:00 +0530"
            },
            {
                "id": "msg002",
                "thread_id": "thread002",
                "sender": "examcell@college.edu",
                "subject": "Mid Semester Examination Schedule",
                "date": "Mon, 16 Nov 2026 11:00:00 +0530"
            },
            {
                "id": "msg003",
                "thread_id": "thread003",
                "sender": "faculty@college.edu",
                "subject": "Lecture notes and study material",
                "date": "Mon, 16 Nov 2026 12:00:00 +0530"
            },
            {
                "id": "msg004",
                "thread_id": "thread004",
                "sender": "unknown@example.com",
                "subject": "Weekend photography",
                "date": "Mon, 16 Nov 2026 13:00:00 +0530"
            }
        ]

        return messages[:max_results]


def run_tests():
    print("Testing Gmail classification service...\n")

    service = GmailClassificationService(reader=FakeGmailReader())
    report = service.classify_recent_messages(max_results=10)

    assert report["total_messages"] == 4
    print("PASS: message count")

    assert report["category_counts"]["assignment"] == 1
    assert report["category_counts"]["assessment"] == 1
    assert report["category_counts"]["course_material"] == 1
    assert report["category_counts"]["other"] == 1
    print("PASS: category counts")

    assert all("body" not in message for message in report["messages"])
    print("PASS: no email body retrieved")

    assert all(message["id"] for message in report["messages"])
    print("PASS: message identifiers preserved")

    try:
        service.classify_recent_messages(max_results=101)
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: max_results validation")

    try:
        service.classify_recent_messages(max_results=True)
        raise AssertionError("Expected TypeError")
    except TypeError:
        print("PASS: input type validation")

    print("\nAll Gmail classification service tests passed.")


if __name__ == "__main__":
    run_tests()
