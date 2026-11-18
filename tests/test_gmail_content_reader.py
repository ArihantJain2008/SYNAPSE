import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.gmail_content_reader import GmailContentReader


def encoded(text):
    return base64.urlsafe_b64encode(
        text.encode("utf-8")
    ).decode("ascii").rstrip("=")


class FakeRequest:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.last_request = None

    def get(self, **kwargs):
        self.last_request = kwargs
        return FakeRequest(self.response)


class FakeUsers:
    def __init__(self, response):
        self.message_api = FakeMessages(response)

    def messages(self):
        return self.message_api


class FakeService:
    def __init__(self, response):
        self.user_api = FakeUsers(response)

    def users(self):
        return self.user_api


def make_part(mime_type, text, headers=None):
    return {
        "mimeType": mime_type,
        "headers": headers or [],
        "body": {"data": encoded(text)}
    }


def run_tests():
    print("Testing Gmail content reader...\n")

    plain_response = {
        "payload": {
            "mimeType": "text/plain",
            "body": {"data": encoded("Assignment due Friday.")}
        }
    }

    service = FakeService(plain_response)
    reader = GmailContentReader(service=service)

    result = reader.read_message("test001")

    assert result["body"] == "Assignment due Friday."
    assert result["format"] == "plain"
    assert result["truncated"] is False
    print("PASS: plain-text extraction")

    assert service.user_api.message_api.last_request["format"] == "full"
    print("PASS: Gmail full-format request")

    html_response = {
        "payload": make_part(
            "text/html",
            "<html><body><h1>Assignment</h1><p>Due Friday</p>"
            "<script>secret()</script></body></html>"
        )
    }

    reader = GmailContentReader(service=FakeService(html_response))
    result = reader.read_message("test002")

    assert "Assignment" in result["body"]
    assert "Due Friday" in result["body"]
    assert "secret" not in result["body"]
    assert result["format"] == "html"
    print("PASS: HTML fallback and script removal")

    multipart_response = {
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                make_part("text/html", "<p>HTML version</p>"),
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        make_part("text/plain", "Plain version"),
                    ]
                },
                {
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "fake-attachment"}
                }
            ]
        }
    }

    reader = GmailContentReader(service=FakeService(multipart_response))
    result = reader.read_message("test003")

    assert result["body"] == "Plain version"
    assert result["format"] == "plain"
    assert result["parts_read"] == 2
    print("PASS: nested MIME and plain-text preference")
    print("PASS: attachments are not downloaded")

    reader = GmailContentReader(
        service=FakeService(plain_response)
    )
    result = reader.read_message("test004", max_chars=5)

    assert result["body"] == "Assig"
    assert result["truncated"] is True
    assert result["original_length"] == len("Assignment due Friday.")
    print("PASS: content length limit")

    try:
        reader.read_message("")
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: message ID validation")

    try:
        reader.read_message("test005", max_chars=True)
        raise AssertionError("Expected TypeError")
    except TypeError:
        print("PASS: max_chars type validation")

    try:
        reader.read_message("test006", max_chars=0)
        raise AssertionError("Expected ValueError")
    except ValueError:
        print("PASS: max_chars range validation")

    print("\nAll Gmail content reader tests passed.")


if __name__ == "__main__":
    run_tests()
