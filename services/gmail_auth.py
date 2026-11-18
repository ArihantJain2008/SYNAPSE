import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_DIR = PROJECT_ROOT / ".secrets"

CLIENT_FILE = SECRETS_DIR / "credentials.json"
TOKEN_FILE = SECRETS_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def validate_configuration():
    """Check local OAuth configuration without exposing credentials."""
    if not CLIENT_FILE.is_file():
        raise FileNotFoundError(
            f"OAuth client file not found: {CLIENT_FILE}"
        )

    try:
        with CLIENT_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)

        if "installed" not in config:
            raise ValueError(
                "OAuth client must be a Desktop app client."
            )

        required = ("client_id", "client_secret", "auth_uri", "token_uri")
        missing = [key for key in required if not config["installed"].get(key)]

        if missing:
            raise ValueError(
                f"OAuth configuration is missing fields: {', '.join(missing)}"
            )

    except json.JSONDecodeError as exc:
        raise ValueError("OAuth client JSON is invalid.") from exc

    return True


def get_gmail_credentials():
    """Load, refresh, or interactively obtain Gmail read-only credentials."""
    validate_configuration()

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_FILE),
            SCOPES
        )

        credentials = flow.run_local_server(
            host="localhost",
            port=0,
            access_type="offline",
            prompt="consent"
        )

    if not credentials.has_scopes(SCOPES):
        raise PermissionError(
            "The saved Google authorization does not include Gmail read-only access."
        )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8"
    )

    return credentials


def get_gmail_service():
    """Build and return an authenticated Gmail API client."""
    credentials = get_gmail_credentials()

    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False
    )
