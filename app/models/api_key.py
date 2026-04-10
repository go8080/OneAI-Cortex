"""API key model — Cortex-local keys for programmatic access (NOT OneAI-Auth JWTs)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin

__all__ = ["ApiKey"]


class ApiKey(UUIDPrimaryKeyMixin, Base):
    """Cortex API key for machine-to-machine access."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
