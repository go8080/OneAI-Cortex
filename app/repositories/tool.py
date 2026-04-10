"""Tool repository — data access for the tool registry."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import Tool

__all__ = ["ToolRepository"]


class ToolRepository:
    """Data access for tool definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> Tool:
        """Insert a new tool record."""
        instance = Tool(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_id(self, tool_id: UUID) -> Tool | None:
        """Get a tool by ID."""
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Tool | None:
        """Get a tool by unique name."""
        stmt = select(Tool).where(Tool.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tools(
        self,
        *,
        framework: str | None = None,
        active_only: bool = True,
    ) -> list[Tool]:
        """List tools with optional framework filter."""
        stmt = select(Tool)
        if framework:
            stmt = stmt.where(Tool.framework == framework)
        if active_only:
            stmt = stmt.where(Tool.is_active.is_(True))
        stmt = stmt.order_by(Tool.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, tool_id: UUID, data: dict) -> Tool | None:
        """Update a tool by ID. Returns None if not found."""
        tool = await self.get_by_id(tool_id)
        if tool is None:
            return None
        for key, value in data.items():
            setattr(tool, key, value)
        await self._session.flush()
        return tool
