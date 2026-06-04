"""Tests for NLP phishing email scorer."""

import pickle
import pytest
from unittest.mock import MagicMock, patch

from app.services.nlp_model import (
    NLPResult,
    _rule_based_score,
    clean_email_text,
    score,
)


class TestCleanEmailText:
    def test_removes_html_tags(self):
        result = clean_email_text("<b>Click</b> here <script>evil()</script>")
        assert "<b>" not in result
        assert "<script>" not in result
        assert "Click" in result

    def test_masks_urls(self):
        result = clean_email_text("Visit https://evil.com/phish?x=1 now")
        assert "https://" not in result
        # [URL] brackets are stripped by the special-char filter that runs next,
        # leaving the bare token "URL" — matching training-time behaviour.
        assert "URL" in result

    def test_filters_special_chars(self):
        result = clean_email_text("Hello!!! Check $$$ this $$$")
        assert "$$$" not in result

    def test_normalizes_whitespace(self):
        result = clean_email_text("too    many     spaces")
        assert "  " not in result

    def test_empty_string(self):
        assert clean_email_text("") == ""

    def test_none_handled(self):
        assert clean_email_text(None) == ""  # type: ignore[arg-type]

    def test_korean_preserved(self):
        result = clean_email_text("계정 확인이 필요합니다")
        assert "계정" in result
        assert "확인" in result


class TestRuleBasedScore:
    def test_no_keywords_score_zero(self):
        score, hits = _rule_based_score("Hello, here is the weekly project update.")
        assert score == 0.0
        assert hits == []

    def test_single_phishing_keyword(self):
        score, hits = _rule_based_score("Please click here to confirm your account.")
        assert score > 0.0
        assert len(hits) >= 1

    def test_multiple_keywords_higher_score(self):
        text = "Urgent: verify your account immediately. Click here to reset your password."
        score_single, _ = _rule_based_score("Click here")
        score_multi, _ = _rule_based_score(text)
        assert score_multi >= score_single

    def test_score_capped_at_one(self):
        many_keywords = " ".join(["click here verify your account urgent suspended"] * 10)
        score, _ = _rule_based_score(many_keywords)
        assert score <= 1.0

    def test_korean_phishing_keyword(self):
        score, hits = _rule_based_score("즉시 확인이 필요합니다. 계정 정지 예정입니다.")
        assert score > 0.0


class TestNLPScore:
    def test_returns_nlpresult(self):
        result = score("Hello", "Normal business email")
        assert isinstance(result, NLPResult)

    def test_score_in_range(self):
        result = score("Hello", "Normal business email")
        assert 0.0 <= result.score <= 1.0

    def test_top_features_is_list(self):
        result = score("Hello", "Normal business email")
        assert isinstance(result.top_features, list)

    def test_phishing_keywords_raise_score(self):
        result_normal = score("Weekly update", "Hi team, see the report.")
        result_phish = score(
            "Urgent: verify your account",
            "Click here to reset your password immediately. Your account will be suspended.",
        )
        assert result_phish.score >= result_normal.score

    def test_no_model_rule_fallback(self):
        # With no model present, should fall back to rule-based
        with patch("app.services.nlp_model._load_model", return_value=None):
            result = score("Urgent verify account", "click here suspended")
            assert result.score > 0.0

    def test_sklearn_model_used_when_present(self):
        mock_pipe = MagicMock()
        mock_pipe.predict_proba.return_value = [[0.05, 0.95]]

        # Patch _load_model directly to return a sklearn model entry
        with patch("app.services.nlp_model._load_model", return_value=("sklearn", mock_pipe)):
            result = score("test subject", "test body")

        assert 0.0 <= result.score <= 1.0
        mock_pipe.predict_proba.assert_called_once()
