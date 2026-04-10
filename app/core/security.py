"""JWT validation and API key hashing — no HTTP awareness, pure security primitives."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from uuid import UUID

from jose import JWTError, jwt

from app.core.exceptions import AuthenticationError

__all__ = ["AuthenticatedUser", "decode_jwt", "generate_api_key", "hash_api_key"]


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Identity extracted from either a JWT or API key."""

    user_id: UUID
    auth_method: str  # "jwt" or "api_key"


def decode_jwt(token: str, secret_key: str, algorithm: str = "HS256") -> dict:
    """Decode and validate a JWT signed by OneAI-Auth.

    Returns the payload dict. Raises AuthenticationError on any failure.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc

    if "sub" not in payload:
        raise AuthenticationError("Token missing 'sub' claim")

    return payload


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns (raw_key, key_hash, key_prefix).
    The raw_key is shown once to the user, then discarded.
    """
    raw_key = f"ctx_{secrets.token_urlsafe(32)}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:8]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """One-way SHA-256 hash of an API key for storage/lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()
