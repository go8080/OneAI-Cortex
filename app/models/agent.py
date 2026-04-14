"""Agent and AgentVersion ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = ["Agent", "AgentVersion"]


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Top-level agent definition owned by a user."""

    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_user_id_is_deleted", "user_id", "is_deleted"),
        Index(
            "uq_agents_user_name_active",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    framework: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="deepagents"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )

    # Relationships
    versions: Mapped[list[AgentVersion]] = relationship(
        back_populates="agent", cascade="all, delete-orphan", order_by="AgentVersion.version.desc()"
    )


class AgentVersion(UUIDPrimaryKeyMixin, Base):
    """Immutable snapshot of an agent's configuration at a specific version."""

    __tablename__ = "agent_versions"
    __table_args__ = (
        UniqueConstraint("agent_id", "version", name="uq_agent_versions_agent_version"),
        Index("ix_agent_versions_agent_id_version", "agent_id", "version", unique=True),
    )

    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    agent: Mapped[Agent] = relationship(back_populates="versions")
