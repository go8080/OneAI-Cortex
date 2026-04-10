"""API key repository — data access for Cortex API keys."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey

__all__ = ["ApiKeyRepository"]


class ApiKeyRepository:
    """Data access for API keys. No business logic — just queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> ApiKey:
        """Insert a new API key record."""
        instance = ApiKey(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Look up an API key by its SHA-256 hash."""
        stmt = select(ApiKey).where(ApiKey.key_hash == key_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[ApiKey]:
        """List all API keys for a user, ordered by creation date."""
        stmt = (
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, key_id: UUID) -> ApiKey | None:
        """Get an API key by ID."""
        stmt = select(ApiKey).where(ApiKey.id == key_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, key_id: UUID, user_id: UUID) -> bool:
        """Revoke (deactivate) an API key. Returns True if found and revoked."""
        key = await self.get_by_id(key_id)
        if key is None or key.user_id != user_id:
            return False
        key.is_active = False
        await self._session.flush()
        return True
