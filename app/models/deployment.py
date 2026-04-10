"""Deployment ORM model — hosted agents and SDK downloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin

__all__ = ["Deployment"]


class Deployment(UUIDPrimaryKeyMixin, Base):
    """A deployed agent — either hosted or as an SDK download."""

    __tablename__ = "deployments"
    __table_args__ = (
        Index("ix_deployments_user_id", "user_id"),
    )

    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    agent_version: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    download_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
