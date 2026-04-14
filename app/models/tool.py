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

    # --- v0.4.0: Auth type for Connected Services ---
    auth_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="api_key"
    )

    # --- v0.2.0: Categorized tool catalog ---
    category: Mapped[str | None] = mapped_column(
        String(30), nullable=True, index=True
    )
    langchain_class: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    required_keys: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # --- v0.2.0: Tool playground test results ---
    test_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="untested"
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    test_detail: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
