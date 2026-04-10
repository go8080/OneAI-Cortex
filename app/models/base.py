"""SQLAlchemy declarative base and shared mixins."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class TimestampMixin:
    """Adds created_at and updated_at columns with server-side defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Soft delete support via is_deleted flag.

    All queries returning user-facing data MUST filter is_deleted=False.
    """

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key with server-side generation."""

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
