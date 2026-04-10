"""MCP server repository — data access for MCP server records."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_server import McpServer

__all__ = ["McpServerRepository"]


class McpServerRepository:
    """Data access for MCP server records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict) -> McpServer:
        """Insert a new MCP server record."""
        instance = McpServer(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_id(self, server_id: UUID) -> McpServer | None:
        """Get an MCP server by ID."""
        stmt = select(McpServer).where(McpServer.id == server_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, *, status: str | None = None
    ) -> list[McpServer]:
        """List MCP servers for a user, optionally filtered by status."""
        stmt = select(McpServer).where(McpServer.user_id == user_id)
        if status:
            stmt = stmt.where(McpServer.status == status)
        stmt = stmt.order_by(McpServer.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, server_id: UUID, data: dict) -> McpServer | None:
        """Update an MCP server. Returns None if not found."""
        server = await self.get_by_id(server_id)
        if server is None:
            return None
        for key, value in data.items():
            setattr(server, key, value)
        await self._session.flush()
        return server

    async def delete(self, server_id: UUID, user_id: UUID) -> bool:
        """Delete an MCP server. Returns True if found and deleted."""
        server = await self.get_by_id(server_id)
        if server is None or server.user_id != user_id:
            return False
        await self._session.delete(server)
        await self._session.flush()
        return True
