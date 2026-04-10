"""Shared FastAPI dependencies for dependency injection."""

from __future__ import annotations

from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import AuthenticatedUser, decode_jwt, hash_api_key


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session, commit on success, rollback on error."""
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """Extract and validate user identity from Authorization header.

    Supports two schemes:
      - "Bearer <jwt>" — decoded locally with shared JWT_SECRET_KEY
      - "ApiKey <raw_key>" — SHA-256 hashed and looked up in api_keys table
    """
    if authorization.startswith("Bearer "):
        token = authorization[7:]
        settings = get_settings()
        payload = decode_jwt(token, settings.jwt_secret_key, settings.jwt_algorithm)
        try:
            user_id = UUID(payload["sub"])
        except (ValueError, KeyError) as exc:
            raise AuthenticationError("Invalid user ID in token") from exc
        return AuthenticatedUser(user_id=user_id, auth_method="jwt")

    if authorization.startswith("ApiKey "):
        raw_key = authorization[7:]
        key_hash = hash_api_key(raw_key)

        from app.models.api_key import ApiKey
        from sqlalchemy import select

        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()

        if api_key is None:
            raise AuthenticationError("Invalid or revoked API key")

        # Update last_used_at
        from datetime import UTC, datetime

        api_key.last_used_at = datetime.now(UTC)
        await db.flush()

        return AuthenticatedUser(user_id=api_key.user_id, auth_method="api_key")

    raise AuthenticationError("Authorization header must start with 'Bearer' or 'ApiKey'")
