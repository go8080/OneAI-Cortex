"""Tests for app.core.security — JWT decode, API key generation, hashing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.exceptions import AuthenticationError
from app.core.security import (
    AuthenticatedUser,
    decode_jwt,
    generate_api_key,
    hash_api_key,
)

SECRET = "test-secret-key-for-unit-tests"
ALGORITHM = "HS256"


def _make_jwt(sub: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", exp_delta: int = 3600, **extra) -> str:
    payload = {
        "sub": sub,
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(seconds=exp_delta),
        **extra,
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


class TestDecodeJWT:
    def test_valid_token(self):
        token = _make_jwt()
        payload = decode_jwt(token, SECRET, ALGORITHM)
        assert payload["sub"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert payload["type"] == "access"

    def test_expired_token_raises(self):
        token = _make_jwt(exp_delta=-10)
        with pytest.raises(AuthenticationError, match="expired|invalid"):
            decode_jwt(token, SECRET, ALGORITHM)

    def test_wrong_secret_raises(self):
        token = _make_jwt()
        with pytest.raises(AuthenticationError):
            decode_jwt(token, "wrong-secret", ALGORITHM)

    def test_malformed_token_raises(self):
        with pytest.raises(AuthenticationError):
            decode_jwt("not.a.jwt", SECRET, ALGORITHM)

    def test_empty_token_raises(self):
        with pytest.raises(AuthenticationError):
            decode_jwt("", SECRET, ALGORITHM)


class TestGenerateApiKey:
    def test_returns_triple(self):
        raw_key, key_hash, key_prefix = generate_api_key()
        assert isinstance(raw_key, str)
        assert isinstance(key_hash, str)
        assert isinstance(key_prefix, str)

    def test_raw_key_starts_with_ctx(self):
        raw_key, _, _ = generate_api_key()
        assert raw_key.startswith("ctx_")

    def test_prefix_matches_raw_key(self):
        raw_key, _, key_prefix = generate_api_key()
        assert raw_key.startswith(key_prefix) or raw_key[4:].startswith(key_prefix[:4])

    def test_hash_is_deterministic_for_same_key(self):
        raw_key, key_hash, _ = generate_api_key()
        assert hash_api_key(raw_key) == key_hash

    def test_different_keys_have_different_hashes(self):
        _, hash1, _ = generate_api_key()
        _, hash2, _ = generate_api_key()
        assert hash1 != hash2


class TestHashApiKey:
    def test_consistent_hash(self):
        assert hash_api_key("ctx_test123") == hash_api_key("ctx_test123")

    def test_different_inputs_different_hashes(self):
        assert hash_api_key("ctx_abc") != hash_api_key("ctx_xyz")

    def test_returns_hex_string(self):
        result = hash_api_key("ctx_test")
        assert all(c in "0123456789abcdef" for c in result)
        assert len(result) == 64  # SHA-256 hex


class TestAuthenticatedUser:
    def test_frozen_dataclass(self):
        user = AuthenticatedUser(
            user_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            auth_method="jwt",
        )
        assert str(user.user_id) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert user.auth_method == "jwt"
