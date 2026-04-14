"""Tool repository — data access for the tool registry."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
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
        category: str | None = None,
        active_only: bool = True,
    ) -> list[Tool]:
        """List tools with optional framework and category filters."""
        stmt = select(Tool)
        if framework:
            stmt = stmt.where(Tool.framework == framework)
        if category:
            stmt = stmt.where(Tool.category == category)
        if active_only:
            stmt = stmt.where(Tool.is_active.is_(True))
        stmt = stmt.order_by(Tool.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_categories(self) -> list[tuple[str, int]]:
        """Return distinct categories with tool counts, ordered by name."""
        stmt = (
            select(Tool.category, func.count().label("tool_count"))
            .where(Tool.is_active.is_(True))
            .where(Tool.category.is_not(None))
            .group_by(Tool.category)
            .order_by(Tool.category)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def update_test_result(
        self,
        tool_id: UUID,
        status: str,
        detail: dict[str, Any],
        tested_at: datetime,
    ) -> Tool | None:
        """Update tool playground test results."""
        tool = await self.get_by_id(tool_id)
        if tool is None:
            return None
        tool.test_status = status
        tool.test_detail = detail
        tool.last_tested_at = tested_at
        await self._session.flush()
        return tool

    async def update(self, tool_id: UUID, data: dict) -> Tool | None:
        """Update a tool by ID. Returns None if not found."""
        tool = await self.get_by_id(tool_id)
        if tool is None:
            return None
        for key, value in data.items():
            setattr(tool, key, value)
        await self._session.flush()
        return tool
