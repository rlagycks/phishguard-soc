"""Gmail API OAuth2 client.

OAuth flow:
  1. Call `get_auth_url()` → redirect user to Google consent screen.
  2. Google redirects to GOOGLE_REDIRECT_URI with `?code=...`.
  3. Call `exchange_code(code)` → saves token to credentials/token_{email}.json.
  4. All subsequent calls use `_get_service(email)` which auto-refreshes the token.

Multi-account: each account's token is stored as token_{sanitized_email}.json.
Legacy token.json is kept for backward compatibility.
"""

import base64
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import get_settings

settings = get_settings()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "credentials"
TOKEN_PATH = CREDENTIALS_DIR / "token.json"
CLIENT_SECRETS_PATH = CREDENTIALS_DIR / "client_secrets.json"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _sanitize_email(email: str) -> str:
    return email.replace("@", "_at_").replace(".", "_")


def get_token_path(email: str) -> Path:
    """Returns per-account token file path, or legacy path if email is empty."""
    if not email:
        return TOKEN_PATH
    return CREDENTIALS_DIR / "token_{}.json".format(_sanitize_email(email))


def get_auth_url() -> str:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(code: str) -> str:
    """Exchange auth code for tokens. Saves per-account token; returns authenticated email."""
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    creds = flow.credentials
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    # Save to legacy path first so _get_service() can work before we know the email
    TOKEN_PATH.write_text(creds.to_json())
    # Resolve the account email and save to per-account path
    try:
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "")
        if email:
            get_token_path(email).write_text(creds.to_json())
        return email
    except Exception:
        return ""


def _load_credentials(email: str = "") -> Optional[Credentials]:
    path = get_token_path(email)
    if not path.exists() and email:
        path = TOKEN_PATH
    if not path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
    return creds


def _get_service(email: str = ""):
    creds = _load_credentials(email)
    if not creds or not creds.valid:
        raise RuntimeError(
            "Gmail credentials not found or invalid. Please complete OAuth flow at /auth/login."
        )
    return build("gmail", "v1", credentials=creds)


# ── Watch management ──────────────────────────────────────────────────────────

def setup_watch(email: str = "") -> dict:
    service = _get_service(email)
    body = {
        "topicName": settings.PUBSUB_TOPIC,
        "labelIds": ["INBOX"],
    }
    return service.users().watch(userId="me", body=body).execute()


def stop_watch(email: str = "") -> None:
    service = _get_service(email)
    service.users().stop(userId="me").execute()


# ── Mail fetching ─────────────────────────────────────────────────────────────

def list_history(start_history_id: str, email: str = "") -> List[dict]:
    """Returns new messages added since start_history_id for the given account."""
    service = _get_service(email)
    messages: List[dict] = []
    try:
        result = (
            service.users()
            .history()
            .list(userId="me", startHistoryId=start_history_id, historyTypes=["messageAdded"])
            .execute()
        )
        for record in result.get("history", []):
            for msg in record.get("messagesAdded", []):
                messages.append(msg["message"])
    except Exception:
        pass
    return messages


def get_message(message_id: str, email: str = "") -> Dict[str, Any]:
    service = _get_service(email)
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


# ── Label / quarantine actions ────────────────────────────────────────────────

def apply_quarantine_label(message_id: str, label_id: str = "QUARANTINE", email: str = "") -> None:
    """Add Quarantine label and remove from INBOX."""
    service = _get_service(email)
    body = {
        "addLabelIds": [label_id],
        "removeLabelIds": ["INBOX"],
    }
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()


def apply_review_label(message_id: str, label_id: str = "NEEDS_REVIEW", email: str = "") -> None:
    service = _get_service(email)
    body = {"addLabelIds": [label_id]}
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()


def ensure_label_exists(label_name: str, email: str = "") -> str:
    """Get or create a Gmail label; returns its ID."""
    service = _get_service(email)
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for lbl in labels:
        if lbl["name"].lower() == label_name.lower():
            return lbl["id"]
    new_label = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "messageListVisibility": "show",
            "labelListVisibility": "labelShow",
        },
    ).execute()
    return new_label["id"]


def get_authenticated_email() -> str:
    """Return the email address of the authenticated Gmail account (legacy token)."""
    service = _get_service()
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def decode_base64_url(data: str) -> str:
    """Decode Gmail base64url-encoded content."""
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
