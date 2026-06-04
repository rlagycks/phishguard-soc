"""Tests for ensemble risk scoring engine."""

import pytest
from app.services.ensemble import run, _classify, EnsembleResult
from app.services.email_parser import ParsedEmail
from datetime import datetime


def _make_parsed(
    subject: str = "Hello",
    body: str = "Normal business email.",
    urls: list | None = None,
    sender: str = "user@company.com",
) -> ParsedEmail:
    return ParsedEmail(
        message_id="test-id",
        history_id="111",
        received_at=datetime(2026, 5, 7, 10, 21),
        sender=sender,
        sender_domain="company.com",
        subject=subject,
        body_text=body,
        body_preview=body[:500],
        urls=urls or [],
        raw_headers={},
    )


class TestClassify:
    def test_normal_below_threshold(self):
        assert _classify(0.10) == "normal"
        assert _classify(0.39) == "normal"

    def test_suspicious_range(self):
        assert _classify(0.40) == "suspicious"
        assert _classify(0.69) == "suspicious"

    def test_dangerous_above_threshold(self):
        assert _classify(0.70) == "dangerous"
        assert _classify(1.00) == "dangerous"


class TestEnsembleRun:
    def test_normal_email_low_score(self):
        parsed = _make_parsed(
            subject="Project update",
            body="Hi team, attached is the weekly report.",
        )
        result = run(parsed)

        assert result.risk_level in ("normal", "suspicious")
        assert 0.0 <= result.final_score <= 1.0

    def test_phishing_keywords_raise_score(self):
        parsed = _make_parsed(
            subject="Urgent: Verify your account immediately",
            body="Click here to reset your password now. Your account will be suspended.",
            urls=["http://phish.xyz/login?verify=1"],
        )
        result = run(parsed)

        assert result.final_score > 0.1
        assert result.nlp_score >= 0.0
        assert result.url_score >= 0.0

    def test_dangerous_url_raises_score(self):
        parsed = _make_parsed(
            subject="Test",
            body="check this out",
            urls=["http://192.168.1.1/phish", "http://login.verify.evil.xyz/account?reset=true"],
        )
        result = run(parsed)

        assert result.url_score > 0.0

    def test_result_fields_valid(self):
        parsed = _make_parsed()
        result = run(parsed)

        assert 0.0 <= result.nlp_score <= 1.0
        assert 0.0 <= result.url_score <= 1.0
        assert 0.0 <= result.rule_score <= 1.0
        assert 0.0 <= result.final_score <= 1.0
        assert result.risk_level in ("normal", "suspicious", "dangerous")

    def test_no_urls_gives_zero_url_score(self):
        parsed = _make_parsed(urls=[])
        result = run(parsed)

        assert result.url_score == 0.0

    def test_final_score_respects_weights(self):
        """Verify weighted sum is within rounding distance."""
        from app.config import get_settings
        s = get_settings()
        parsed = _make_parsed()
        result = run(parsed)

        expected = (
            s.EMAIL_WEIGHT * result.nlp_score
            + s.URL_WEIGHT * result.url_score
            + s.RULE_WEIGHT * result.rule_score
        )
        assert abs(result.final_score - round(expected, 4)) < 1e-3
