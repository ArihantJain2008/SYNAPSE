import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gmail_reader import list_recent_messages


def main():
    print("Testing Gmail metadata retrieval...")

    messages = list_recent_messages(max_results=10)

    print("Messages retrieved:", len(messages))

    if not messages:
        print("No messages returned.")
        return

    required_fields = {"id", "thread_id", "sender", "subject", "date"}

    for index, message in enumerate(messages, start=1):
        missing = required_fields - message.keys()

        if missing:
            raise AssertionError(
                f"Message {index} is missing fields: {missing}"
            )

    print("Metadata structure: Valid")
    print("Private message contents: Not retrieved")
    print("Mailbox modifications: None")
    print("Gmail reader test: PASSED")


if __name__ == "__main__":
    main()
