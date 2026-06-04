"""Decides and executes Gmail label actions based on risk level."""

from app.config import get_settings
from app.services import gmail_client
from app.services.ensemble import EnsembleResult

settings = get_settings()

# Label names created in Gmail automatically on first run
LABEL_QUARANTINE = "Phishing-Quarantine"
LABEL_REVIEW = "Phishing-NeedsReview"

_label_cache: dict[str, str] = {}


def _get_label_id(name: str) -> str:
    if name not in _label_cache:
        _label_cache[name] = gmail_client.ensure_label_exists(name)
    return _label_cache[name]


def execute(message_id: str, result: EnsembleResult) -> str:
    """Apply Gmail labels and return the action string taken."""
    if result.risk_level == "dangerous":
        label_id = _get_label_id(LABEL_QUARANTINE)
        gmail_client.apply_quarantine_label(message_id, label_id)
        return "quarantined"

    if result.risk_level == "suspicious":
        label_id = _get_label_id(LABEL_REVIEW)
        gmail_client.apply_review_label(message_id, label_id)
        return "needs_review"

    return "normal"
