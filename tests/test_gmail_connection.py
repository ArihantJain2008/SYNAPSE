import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.gmail_auth import get_gmail_service, TOKEN_FILE

EXPECTED_EMAIL = "arihant.jain@bcah.christuniversity.in"


def main():
    print("Starting Google OAuth...")
    print("Choose your COLLEGE Google account in the browser.")

    service = get_gmail_service()

    profile = service.users().getProfile(userId="me").execute()
    actual_email = profile.get("emailAddress", "").lower()

    if actual_email != EXPECTED_EMAIL.lower():
        TOKEN_FILE.unlink(missing_ok=True)
        raise RuntimeError(
            f"Wrong Google account authorized: {actual_email}. "
            "Saved token deleted. Run this test again."
        )

    print("\nSUCCESS: College Gmail connected.")
    print("Verified account:", actual_email)
    print("Total messages:", profile.get("messagesTotal"))
    print("Total threads:", profile.get("threadsTotal"))
    print("OAuth token saved locally.")
    print("Access granted: Gmail read-only.")


if __name__ == "__main__":
    main()
