import base64
import re
from email.message import Message
from html.parser import HTMLParser

from services.gmail_auth import get_gmail_service


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style"):
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style") and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            text = data.strip()
            if text:
                self.parts.append(text)

    def get_text(self):
        return "\n".join(self.parts)


def _decode_part(part):
    data = part.get("body", {}).get("data")

    if not data:
        return ""

    try:
        decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    except Exception as exc:
        raise ValueError("Could not decode Gmail message content.") from exc

    content_type = "text/plain"

    for header in part.get("headers", []):
        if header.get("name", "").lower() == "content-type":
            content_type = header.get("value", content_type)
            break

    metadata = Message()
    metadata["content-type"] = content_type
    charset = metadata.get_content_charset() or "utf-8"

    try:
        return decoded.decode(charset, errors="replace")
    except LookupError:
        return decoded.decode("utf-8", errors="replace")


def _collect_text_parts(payload):
    plain_parts = []
    html_parts = []
    parts_read = 0

    def visit(part):
        nonlocal parts_read

        mime_type = part.get("mimeType", "").lower()

        if mime_type == "text/plain":
            text = _decode_part(part)
            if text:
                plain_parts.append(text)
                parts_read += 1

        elif mime_type == "text/html":
            html = _decode_part(part)
            if html:
                html_parts.append(html)
                parts_read += 1

        for child in part.get("parts", []):
            visit(child)

    visit(payload)

    return plain_parts, html_parts, parts_read


def _html_to_text(html):
    parser = _HTMLTextExtractor()
    parser.feed(html)
    parser.close()

    return parser.get_text()


class GmailContentReader:
    """
    Retrieves and extracts email text using Gmail's read-only API.

    Attachments are not downloaded or processed.
    """

    def __init__(self, service=None):
        self.service = service

    def read_message(self, message_id, max_chars=50000):
        if not isinstance(message_id, str) or not message_id.strip():
            raise ValueError("message_id must be a non-empty string")

        if not isinstance(max_chars, int) or isinstance(max_chars, bool):
            raise TypeError("max_chars must be an integer")

        if max_chars < 1:
            raise ValueError("max_chars must be greater than zero")

        service = self.service or get_gmail_service()

        message = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
        ).execute()

        payload = message.get("payload", {})

        plain_parts, html_parts, parts_read = _collect_text_parts(payload)

        if plain_parts:
            body = "\n\n".join(plain_parts)
            body_format = "plain"
        elif html_parts:
            body = "\n\n".join(
                _html_to_text(part) for part in html_parts
            )
            body_format = "html"
        else:
            body = ""
            body_format = "empty"

        body = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", body).strip()

        truncated = len(body) > max_chars

        return {
            "message_id": message_id,
            "body": body[:max_chars],
            "format": body_format,
            "truncated": truncated,
            "original_length": len(body),
            "parts_read": parts_read
        }
