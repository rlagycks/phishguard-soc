"""Tests for URL phishing risk scorer (URLClassifier)."""

import pickle
import pytest
from unittest.mock import MagicMock, patch

from app.services.url_model import URLClassifier, URLModelResult, _heuristic_score, score_urls
from app.services.url_extractor import extract_features


class TestURLClassifier:
    def test_instantiate_no_model(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        assert clf._backend == "heuristic"
        assert clf._model is None

    def test_score_urls_empty_list(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        result = clf.score_urls([])
        assert result.max_score == 0.0
        assert result.avg_score == 0.0
        assert result.per_url == []

    def test_score_urls_returns_urlmodelresult(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        result = clf.score_urls(["https://example.com"])
        assert isinstance(result, URLModelResult)

    def test_score_urls_single_url_fields(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        result = clf.score_urls(["https://example.com/path"])
        assert len(result.per_url) == 1
        entry = result.per_url[0]
        assert "url" in entry
        assert "score" in entry
        assert "is_https" in entry
        assert "is_ip" in entry
        assert "suspicious_tld" in entry
        assert "phishing_keywords" in entry

    def test_ip_url_high_score(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        result = clf.score_urls(["http://192.168.1.1/login/verify"])
        assert result.max_score > 0.3

    def test_https_normal_url_lower_score(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        result = clf.score_urls(["https://www.naver.com"])
        # Normal URL with no suspicious features should score low
        assert result.max_score < 0.5

    def test_multiple_urls_max_score_correct(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        urls = [
            "https://www.google.com",
            "http://192.168.0.1/phish/verify?account=reset",
        ]
        result = clf.score_urls(urls)
        assert result.max_score >= result.avg_score
        assert len(result.per_url) == 2

    def test_score_single_returns_dict(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        entry = clf.score_single("https://example.com")
        assert isinstance(entry, dict)
        assert "score" in entry

    def test_backend_label_heuristic(self, tmp_path):
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        result = clf.score_urls(["https://example.com"])
        assert result.backend == "heuristic"

    def test_sklearn_model_loaded(self, tmp_path):
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.1, 0.9]]

        # Directly inject mock model (MagicMock cannot be pickled)
        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        clf._model = mock_model
        clf._backend = "sklearn"

        result = clf.score_urls(["http://evil.xyz/login"])
        assert result.backend == "sklearn"
        assert result.max_score == pytest.approx(0.9)

    def test_sklearn_model_exception_falls_back(self, tmp_path):
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = RuntimeError("model broken")

        clf = URLClassifier(tmp_path / "nonexistent.pkl")
        clf._model = mock_model
        clf._backend = "sklearn"

        # Should not raise; falls back to heuristic silently
        result = clf.score_urls(["https://example.com"])
        assert 0.0 <= result.max_score <= 1.0


class TestHeuristicScore:
    def test_ip_address_adds_score(self):
        f = extract_features("http://192.168.1.1/login")
        score = _heuristic_score(f)
        assert score >= 0.30

    def test_suspicious_tld_adds_score(self):
        f = extract_features("http://evil.xyz/page")
        score = _heuristic_score(f)
        assert score >= 0.20

    def test_score_capped_at_one(self):
        f = extract_features("http://192.168.1.1/login/verify/account?reset=1&confirm=1&password=abc")
        score = _heuristic_score(f)
        assert score <= 1.0

    def test_normal_url_low_score(self):
        f = extract_features("https://www.github.com")
        score = _heuristic_score(f)
        assert score < 0.3


class TestModuleLevelScoreUrls:
    def test_module_score_urls_works(self):
        result = score_urls(["https://example.com"])
        assert isinstance(result, URLModelResult)
        assert result.max_score >= 0.0

    def test_module_score_urls_empty(self):
        result = score_urls([])
        assert result.max_score == 0.0
