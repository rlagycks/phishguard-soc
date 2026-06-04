"""Parse a raw Gmail API message object into structured fields."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from app.services.gmail_client import decode_base64_url


@dataclass
class ParsedEmail:
    message_id: str
    history_id: str | None
    received_at: datetime | None
    sender: str
    sender_domain: str
    subject: str
    body_text: str
    body_preview: str  # first 500 chars
    urls: list[str]
    raw_headers: dict[str, str]


_URL_PATTERN = re.compile(
    r"https?://[^\s\"'<>]+",
    re.IGNORECASE,
)

_EMAIL_DOMAIN_RE = re.compile(r"@([\w.\-]+)>?$")


def _extract_headers(headers: list[dict]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in headers}


def _get_body_parts(payload: dict, parts: list[str]) -> None:
    """Recursively walk the MIME tree and collect text/plain content."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            parts.append(decode_base64_url(data))
    elif mime.startswith("multipart/"):
        for part in payload.get("parts", []):
            _get_body_parts(part, parts)


def _sender_domain(from_header: str) -> str:
    m = _EMAIL_DOMAIN_RE.search(from_header)
    return m.group(1).lower() if m else ""


def parse_gmail_message(raw: dict[str, Any]) -> ParsedEmail:
    payload = raw.get("payload", {})
    headers = _extract_headers(payload.get("headers", []))

    sender = headers.get("from", "")
    subject = headers.get("subject", "(no subject)")
    date_str = headers.get("date", "")

    received_at: datetime | None = None
    if date_str:
        try:
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            pass

    body_parts: list[str] = []
    _get_body_parts(payload, body_parts)
    body_text = "\n".join(body_parts).strip()

    urls = list(dict.fromkeys(_URL_PATTERN.findall(body_text)))  # deduplicated, ordered

    return ParsedEmail(
        message_id=raw.get("id", ""),
        history_id=str(raw.get("historyId", "")) or None,
        received_at=received_at,
        sender=sender,
        sender_domain=_sender_domain(sender),
        subject=subject,
        body_text=body_text,
        body_preview=body_text[:500],
        urls=urls,
        raw_headers=headers,
    )
