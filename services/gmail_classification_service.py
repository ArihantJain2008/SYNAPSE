from collections import Counter

from services.gmail_reader import list_recent_messages
from services.academic_email_classifier import classify_message


class GmailClassificationService:
    def __init__(self, reader=None):
        self.reader = reader

    def classify_recent_messages(self, max_results=10):
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise TypeError("max_results must be an integer")

        if not 1 <= max_results <= 100:
            raise ValueError("max_results must be between 1 and 100")

        if self.reader is None:
            messages = list_recent_messages(max_results=max_results)
        else:
            messages = self.reader.list_recent_messages(
                max_results=max_results
            )

        results = []

        for message in messages:
            classification = classify_message(message)

            results.append({
                "id": message["id"],
                "thread_id": message["thread_id"],
                "sender": message["sender"],
                "subject": message["subject"],
                "date": message["date"],
                **classification
            })

        category_counts = Counter(
            result["category"] for result in results
        )

        return {
            "total_messages": len(results),
            "category_counts": dict(category_counts),
            "messages": results
        }

    @staticmethod
    def print_report(report):
        print("\nACADEMIC EMAIL CLASSIFICATION REPORT")
        print("=" * 45)
        print(f"Messages processed: {report['total_messages']}")

        print("\nCategory breakdown:")
        for category, count in sorted(report["category_counts"].items()):
            print(f"  {category}: {count}")

        print("\nClassified messages:")
        for message in report["messages"]:
            print("-" * 45)
            print(f"Subject: {message['subject'] or '(No subject)'}")
            print(f"Sender: {message['sender'] or '(Unknown sender)'}")
            print(f"Category: {message['category']}")
            print(f"Confidence: {message['confidence']:.2f}")
            print(f"Requires further review: {message['requires_body']}")

