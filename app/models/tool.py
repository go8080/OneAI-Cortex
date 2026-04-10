"""Tool ORM model — builtin and custom tool definitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin

__all__ = ["Tool"]


class Tool(UUIDPrimaryKeyMixin, Base):
    """A tool available to agents. Schema defines input/output contract."""

    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    framework: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="builtin"
    )
    schema_def: Mapped[dict[str, Any]] = mapped_column(
        "schema", JSONB, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    auth_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
