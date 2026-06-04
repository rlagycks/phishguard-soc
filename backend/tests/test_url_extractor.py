"""Tests for URL feature extractor."""

import pytest
from app.services.url_extractor import extract_features


class TestExtractFeatures:
    def test_https_detected(self):
        f = extract_features("https://example.com/page")
        assert f.is_https is True

    def test_http_not_https(self):
        f = extract_features("http://example.com/")
        assert f.is_https is False

    def test_ip_address_detected(self):
        f = extract_features("http://192.168.1.100/phish")
        assert f.is_ip_address is True

    def test_domain_name_not_ip(self):
        f = extract_features("https://google.com/")
        assert f.is_ip_address is False

    def test_suspicious_tld(self):
        f = extract_features("http://example.xyz/login")
        assert f.suspicious_tld is True

    def test_safe_tld(self):
        f = extract_features("https://example.com/page")
        assert f.suspicious_tld is False

    def test_url_shortener_detected(self):
        f = extract_features("https://bit.ly/abc123")
        assert f.shortener is True

    def test_phishing_keywords_counted(self):
        f = extract_features("https://bank.com/verify/login?account=reset")
        assert f.phishing_keyword_count >= 2

    def test_at_symbol_detected(self):
        f = extract_features("http://user@evil.com/page")
        assert f.at_symbol is True

    def test_feature_vector_length(self):
        f = extract_features("https://example.com/path?q=1")
        assert len(f.to_list()) == 16

    def test_query_params_counted(self):
        f = extract_features("https://example.com/page?a=1&b=2&c=3")
        assert f.query_param_count == 3

    def test_subdomain_counting(self):
        f = extract_features("https://mail.google.com/inbox")
        assert f.subdomain_count == 1
