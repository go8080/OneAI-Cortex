"""Generic CRUD base repository for SQLAlchemy models."""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic CRUD operations. Subclass per model for domain-specific queries."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, id: UUID) -> T | None:
        """Get a single record by primary key."""
        stmt = select(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new record from a dictionary of column values."""
        instance = self._model(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(self, id: UUID, data: dict[str, Any]) -> T:
        """Update a record by ID. Raises if not found."""
        instance = await self.get_by_id(id)
        if instance is None:
            raise ValueError(f"{self._model.__name__} with id={id} not found")
        for key, value in data.items():
            setattr(instance, key, value)
        await self._session.flush()
        return instance

    async def soft_delete(self, id: UUID) -> None:
        """Soft-delete a record by setting is_deleted=True."""
        instance = await self.get_by_id(id)
        if instance is None:
            raise ValueError(f"{self._model.__name__} with id={id} not found")
        instance.is_deleted = True
        await self._session.flush()

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[T]:
        """List records with optional filters and pagination."""
        stmt = select(self._model)
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self._model, key) == value)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filters."""
        stmt = select(func.count()).select_from(self._model)
        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(self._model, key) == value)
        result = await self._session.execute(stmt)
        return result.scalar_one()
