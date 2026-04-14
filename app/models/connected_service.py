"""ConnectedService ORM model — OAuth connections to external providers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = ["ConnectedService"]


class ConnectedService(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """OAuth connection to an external service provider (Google, Slack, etc.)."""

    __tablename__ = "connected_services"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider", name="uq_connected_services_user_provider"
        ),
        Index("ix_connected_services_user_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    granted_scopes: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=""
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
