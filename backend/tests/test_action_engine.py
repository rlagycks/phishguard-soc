"""Tests for action_engine — Gmail label application logic."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.action_engine import execute
from app.services.ensemble import EnsembleResult
from app.services.nlp_model import NLPResult
from app.services.url_model import URLModelResult


def _make_ensemble_result(risk_level: str, final_score: float) -> EnsembleResult:
    return EnsembleResult(
        nlp_score=0.5,
        url_score=0.5,
        rule_score=0.1,
        final_score=final_score,
        risk_level=risk_level,
        nlp_details=NLPResult(score=0.5, top_features=[]),
        url_details=URLModelResult(max_score=0.5, avg_score=0.5, per_url=[], backend="heuristic"),
        rule_details={},
    )


class TestExecute:
    @patch("app.services.action_engine.gmail_client")
    def test_dangerous_applies_quarantine(self, mock_gmail):
        mock_gmail.ensure_label_exists.return_value = "LABEL_123"
        result = _make_ensemble_result("dangerous", 0.85)

        action = execute("msg-001", result)

        assert action == "quarantined"
        mock_gmail.apply_quarantine_label.assert_called_once_with("msg-001", "LABEL_123")

    @patch("app.services.action_engine.gmail_client")
    def test_suspicious_applies_review_label(self, mock_gmail):
        mock_gmail.ensure_label_exists.return_value = "LABEL_456"
        result = _make_ensemble_result("suspicious", 0.55)

        action = execute("msg-002", result)

        assert action == "needs_review"
        mock_gmail.apply_review_label.assert_called_once_with("msg-002", "LABEL_456")

    @patch("app.services.action_engine.gmail_client")
    def test_normal_no_gmail_calls(self, mock_gmail):
        result = _make_ensemble_result("normal", 0.15)

        action = execute("msg-003", result)

        assert action == "normal"
        mock_gmail.apply_quarantine_label.assert_not_called()
        mock_gmail.apply_review_label.assert_not_called()

    @patch("app.services.action_engine.gmail_client")
    def test_label_cached_after_first_call(self, mock_gmail):
        mock_gmail.ensure_label_exists.return_value = "LABEL_999"
        result = _make_ensemble_result("dangerous", 0.90)

        # Clear label cache between test runs
        import app.services.action_engine as ae
        ae._label_cache.clear()

        execute("msg-a", result)
        execute("msg-b", result)

        # ensure_label_exists should only be called once (cached)
        assert mock_gmail.ensure_label_exists.call_count == 1

    @patch("app.services.action_engine.gmail_client")
    def test_quarantine_label_name_correct(self, mock_gmail):
        mock_gmail.ensure_label_exists.return_value = "LABEL_Q"
        result = _make_ensemble_result("dangerous", 0.80)

        import app.services.action_engine as ae
        ae._label_cache.clear()

        execute("msg-x", result)

        called_with = mock_gmail.ensure_label_exists.call_args[0][0]
        assert called_with == "Phishing-Quarantine"

    @patch("app.services.action_engine.gmail_client")
    def test_review_label_name_correct(self, mock_gmail):
        mock_gmail.ensure_label_exists.return_value = "LABEL_R"
        result = _make_ensemble_result("suspicious", 0.55)

        import app.services.action_engine as ae
        ae._label_cache.clear()

        execute("msg-y", result)

        called_with = mock_gmail.ensure_label_exists.call_args[0][0]
        assert called_with == "Phishing-NeedsReview"
