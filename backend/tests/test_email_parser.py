"""Tests for email_parser module."""

import pytest
from app.services.email_parser import parse_gmail_message, _extract_headers


def _make_raw_message(
    msg_id: str = "abc123",
    from_: str = "attacker@evil.com",
    subject: str = "Verify your account",
    body_text: str = "Click here: https://phish.site/login",
    history_id: str = "12345",
) -> dict:
    import base64
    encoded_body = base64.urlsafe_b64encode(body_text.encode()).decode().rstrip("=")
    return {
        "id": msg_id,
        "historyId": history_id,
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": from_},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Tue, 07 May 2026 10:21:00 +0000"},
            ],
            "body": {"data": encoded_body},
        },
    }


class TestParseGmailMessage:
    def test_basic_fields_extracted(self):
        raw = _make_raw_message()
        parsed = parse_gmail_message(raw)

        assert parsed.message_id == "abc123"
        assert parsed.sender == "attacker@evil.com"
        assert parsed.subject == "Verify your account"
        assert parsed.sender_domain == "evil.com"

    def test_url_extracted_from_body(self):
        raw = _make_raw_message(body_text="Visit https://phish.xyz/steal?x=1 now")
        parsed = parse_gmail_message(raw)

        assert "https://phish.xyz/steal?x=1" in parsed.urls

    def test_multiple_urls_deduplicated(self):
        body = "https://evil.com/path https://evil.com/path https://other.com"
        raw = _make_raw_message(body_text=body)
        parsed = parse_gmail_message(raw)

        assert len(parsed.urls) == 2

    def test_body_preview_max_500_chars(self):
        long_body = "A" * 600
        raw = _make_raw_message(body_text=long_body)
        parsed = parse_gmail_message(raw)

        assert len(parsed.body_preview) == 500

    def test_no_subject_fallback(self):
        raw = _make_raw_message()
        raw["payload"]["headers"] = [h for h in raw["payload"]["headers"] if h["name"] != "Subject"]
        parsed = parse_gmail_message(raw)

        assert parsed.subject == "(no subject)"

    def test_received_at_parsed(self):
        raw = _make_raw_message()
        parsed = parse_gmail_message(raw)

        assert parsed.received_at is not None
        assert parsed.received_at.year == 2026

    def test_empty_body(self):
        raw = _make_raw_message(body_text="")
        # Remove the encoded body entirely
        raw["payload"]["body"] = {}
        parsed = parse_gmail_message(raw)

        assert parsed.body_text == ""
        assert parsed.urls == []


class TestExtractHeaders:
    def test_lowercases_header_names(self):
        headers = [{"name": "From", "value": "test@example.com"}]
        result = _extract_headers(headers)
        assert "from" in result
        assert result["from"] == "test@example.com"
