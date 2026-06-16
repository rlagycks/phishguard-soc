"""Decides and executes Gmail label actions based on risk level."""

from typing import Dict

from app.config import get_settings
from app.services import gmail_client
from app.services.ensemble import EnsembleResult

settings = get_settings()

LABEL_QUARANTINE = "Phishing-Quarantine"
LABEL_REVIEW = "Phishing-NeedsReview"

# Per-account label cache: {email: {label_name: label_id}}
_label_cache: Dict[str, Dict[str, str]] = {}


def _get_label_id(name: str, email: str = "") -> str:
    account_cache = _label_cache.setdefault(email, {})
    if name not in account_cache:
        account_cache[name] = gmail_client.ensure_label_exists(name, email=email)
    return account_cache[name]


def execute(message_id: str, result: EnsembleResult, email: str = "") -> str:
    """Apply Gmail labels for the given account and return the action string taken."""
    if result.risk_level == "dangerous":
        label_id = _get_label_id(LABEL_QUARANTINE, email)
        gmail_client.apply_quarantine_label(message_id, label_id, email=email)
        return "quarantined"

    if result.risk_level == "suspicious":
        label_id = _get_label_id(LABEL_REVIEW, email)
        gmail_client.apply_review_label(message_id, label_id, email=email)
        return "needs_review"

    return "normal"
