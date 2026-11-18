from collections import Counter

from services.gmail_classification_service import GmailClassificationService
from services.gmail_content_reader import GmailContentReader


BODY_RETRIEVAL_CATEGORIES = {
    "assignment",
    "assessment",
    "announcement",
    "course_material",
    "schedule_change",
    "general_college",
    "academic_opportunity",
    "course_update",
}


class GmailAcademicProcessingService:
    """
    Classifies Gmail messages and selectively retrieves academic bodies.
    Email bodies are returned to the caller but are not persisted or logged.
    """

    def __init__(self, classification_service=None, content_reader=None):
        self.classification_service = (
            classification_service or GmailClassificationService()
        )
        self.content_reader = content_reader or GmailContentReader()

    def process_recent_messages(self, max_results=10, max_body_chars=50000):
        if (
            not isinstance(max_body_chars, int)
            or isinstance(max_body_chars, bool)
        ):
            raise TypeError("max_body_chars must be an integer")

        if max_body_chars < 1:
            raise ValueError("max_body_chars must be at least 1")

        report = self.classification_service.classify_recent_messages(
            max_results=max_results
        )

        processed = []
        body_counts = Counter()

        for message in report["messages"]:
            category = message["category"]

            result = {
                **message,
                "body": None,
                "body_format": None,
                "body_truncated": False,
                "body_status": None,
                "review_required": bool(message.get("requires_body", False)),
            }

            if category == "promotional":
                result["body_status"] = "skipped_promotional"
                body_counts["skipped_promotional"] += 1

            elif category not in BODY_RETRIEVAL_CATEGORIES:
                result["body_status"] = "skipped_uncategorized"
                result["review_required"] = True
                body_counts["skipped_uncategorized"] += 1

            else:
                try:
                    content = self.content_reader.read_message(
                        message_id=message["id"],
                        max_chars=max_body_chars,
                    )

                    result["body"] = content["body"]
                    result["body_format"] = content["format"]
                    result["body_truncated"] = content["truncated"]
                    result["body_status"] = (
                        "empty" if not content["body"] else "retrieved"
                    )

                    if not content["body"] or content["truncated"]:
                        result["review_required"] = True

                    if not content["body"]:
                        body_counts["empty"] += 1
                    else:
                        body_counts["retrieved"] += 1

                except Exception as exc:
                    result["body_status"] = "retrieval_failed"
                    result["retrieval_error"] = type(exc).__name__
                    result["review_required"] = True
                    body_counts["retrieval_failed"] += 1

            processed.append(result)

        return {
            "total_messages": len(processed),
            "body_counts": dict(body_counts),
            "messages": processed,
        }
