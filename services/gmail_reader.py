from services.gmail_auth import get_gmail_service


def list_recent_messages(max_results=10):
    """Retrieve recent Gmail headers without retaining message previews."""
    if not isinstance(max_results, int) or not 1 <= max_results <= 100:
        raise ValueError("max_results must be between 1 and 100.")

    service = get_gmail_service()

    response = service.users().messages().list(
        userId="me",
        maxResults=max_results
    ).execute()

    results = []

    for message_ref in response.get("messages", []):
        message = service.users().messages().get(
            userId="me",
            id=message_ref["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()

        headers = {
            header["name"].lower(): header["value"]
            for header in message.get("payload", {}).get("headers", [])
        }

        results.append({
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "sender": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", "")
        })

    return results
