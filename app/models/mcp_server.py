"""MCP Server and agent-MCP junction ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = ["AgentMcpServer", "McpServer"]


class McpServer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An MCP server registered by a user."""

    __tablename__ = "mcp_servers"
    __table_args__ = (
        Index("ix_mcp_servers_user_status", "user_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transport: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    command: Mapped[str | None] = mapped_column(String(500), nullable=True)
    args: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    env_vars: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    auth_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="untested"
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tools_discovered: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )


class AgentMcpServer(Base):
    """Junction table linking agents to MCP servers."""

    __tablename__ = "agent_mcp_servers"

    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    mcp_server_id: Mapped[UUID] = mapped_column(
        ForeignKey("mcp_servers.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
