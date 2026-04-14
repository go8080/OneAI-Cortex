"""Connected service repository — data access for OAuth provider connections."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connected_service import ConnectedService

__all__ = ["ConnectedServiceRepository"]


class ConnectedServiceRepository:
    """Data access for connected service records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> ConnectedService:
        """Create a new connected service record."""
        instance = ConnectedService(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_user_and_provider(
        self, user_id: UUID, provider: str
    ) -> ConnectedService | None:
        """Get a connection by user + provider. Returns None if not found."""
        stmt = select(ConnectedService).where(
            ConnectedService.user_id == user_id,
            ConnectedService.provider == provider,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, service_id: UUID, data: dict[str, Any]
    ) -> ConnectedService | None:
        """Update a connected service. Returns None if not found."""
        stmt = select(ConnectedService).where(ConnectedService.id == service_id)
        result = await self._session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def list_by_user(self, user_id: UUID) -> list[ConnectedService]:
        """List all connected services for a user."""
        stmt = (
            select(ConnectedService)
            .where(ConnectedService.user_id == user_id)
            .order_by(ConnectedService.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, service_id: UUID) -> bool:
        """Hard-delete a connected service. Returns True if found and deleted."""
        stmt = select(ConnectedService).where(ConnectedService.id == service_id)
        result = await self._session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
