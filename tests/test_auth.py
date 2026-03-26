"""
Unit tests for server/auth.py — JWT token creation and verification.
"""
import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

import config as _cfg
_cfg.DATABASE_URL = ":memory:"

import auth


class TestAuth:
    def test_create_token_returns_string(self):
        token = auth.create_token(1, "alice")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        token = auth.create_token(42, "bob")
        data = auth.verify_token(token)
        assert data is not None
        assert data["user_id"] == 42
        assert data["username"] == "bob"

    def test_verify_invalid_token_returns_none(self):
        assert auth.verify_token("not.a.token") is None

    def test_verify_tampered_token_returns_none(self):
        token = auth.create_token(1, "alice")
        # Corrupt the signature part
        parts = token.split(".")
        parts[-1] = "badsignature"
        assert auth.verify_token(".".join(parts)) is None

    def test_verify_expired_token_returns_none(self, monkeypatch):
        """Simulate an already-expired token by setting expiry hours to 0."""
        import datetime

        original = auth.create_token

        def make_expired_token(user_id, username):
            import jwt
            payload = {
                "user_id": user_id,
                "username": username,
                "exp": datetime.datetime.now(datetime.timezone.utc)
                       - datetime.timedelta(seconds=1),
            }
            return jwt.encode(payload, _cfg.SECRET_KEY, algorithm=_cfg.JWT_ALGORITHM)

        monkeypatch.setattr(auth, "create_token", make_expired_token)
        token = auth.create_token(1, "expireduser")
        assert auth.verify_token(token) is None
