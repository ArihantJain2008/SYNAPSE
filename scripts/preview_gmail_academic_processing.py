import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gmail_academic_processing_service import (
    GmailAcademicProcessingService,
)


def main():
    print("Starting read-only Gmail academic processing test...")
    print("Maximum messages: 10")
    print("Email bodies will NOT be displayed or saved.\n")

    service = GmailAcademicProcessingService()
    report = service.process_recent_messages(max_results=10)

    print("=" * 65)
    print("GMAIL ACADEMIC PROCESSING REPORT")
    print("=" * 65)
    print(f"Messages processed: {report['total_messages']}")

    print("\nBody retrieval summary:")
    if report["body_counts"]:
        for status, count in sorted(report["body_counts"].items()):
            print(f"  {status}: {count}")
    else:
        print("  No body retrieval attempts.")

    print("\nIndividual messages:")
    for index, message in enumerate(report["messages"], start=1):
        print("-" * 65)
        print(f"{index}. {message.get('subject') or '(No subject)'}")
        print(f"   Category: {message['category']}")
        print(f"   Confidence: {message['confidence']:.2f}")
        print(f"   Body status: {message['body_status']}")
        print(f"   Review required: {message['review_required']}")

    print("\nTest completed. No email content was printed or persisted.")


if __name__ == "__main__":
    main()
