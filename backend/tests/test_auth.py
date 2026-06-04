"""Unit tests for JWT auth utilities."""

import time
import pytest
from unittest.mock import patch
from jose import jwt

from app.services.auth import create_access_token, create_refresh_token, decode_token


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only")
    # Clear lru_cache so settings picks up the new env var
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token("user@example.com")
        assert isinstance(token, str)

    def test_contains_email_claim(self):
        token = create_access_token("user@example.com")
        payload = decode_token(token)
        assert payload is not None
        assert payload["email"] == "user@example.com"
        assert payload["sub"] == "user@example.com"

    def test_type_is_access(self):
        token = create_access_token("user@example.com")
        payload = decode_token(token)
        assert payload["type"] == "access"

    def test_has_exp_claim(self):
        token = create_access_token("user@example.com")
        payload = decode_token(token)
        assert "exp" in payload

    def test_different_emails_produce_different_tokens(self):
        t1 = create_access_token("a@example.com")
        t2 = create_access_token("b@example.com")
        assert t1 != t2


class TestCreateRefreshToken:
    def test_type_is_refresh(self):
        token = create_refresh_token("user@example.com")
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_longer_expiry_than_access(self):
        access = create_access_token("user@example.com")
        refresh = create_refresh_token("user@example.com")
        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)
        assert refresh_payload["exp"] > access_payload["exp"]


class TestDecodeToken:
    def test_valid_token_returns_payload(self):
        token = create_access_token("user@example.com")
        payload = decode_token(token)
        assert payload is not None
        assert payload["email"] == "user@example.com"

    def test_invalid_token_returns_none(self):
        assert decode_token("not.a.valid.token") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("user@example.com")
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_wrong_secret_returns_none(self):
        from app.config import get_settings
        s = get_settings()
        token = jwt.encode(
            {"sub": "user@example.com", "email": "user@example.com"},
            "wrong-secret",
            algorithm=s.JWT_ALGORITHM,
        )
        assert decode_token(token) is None

    def test_expired_token_returns_none(self):
        from datetime import datetime, timezone
        from jose import jwt as jose_jwt
        from app.config import get_settings
        s = get_settings()
        past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        token = jose_jwt.encode(
            {"sub": "user@example.com", "exp": past},
            s.JWT_SECRET_KEY,
            algorithm=s.JWT_ALGORITHM,
        )
        assert decode_token(token) is None
