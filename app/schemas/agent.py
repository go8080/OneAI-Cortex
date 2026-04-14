"""Pydantic schemas for agent builder endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "AgentCreate",
    "AgentResponse",
    "AgentUpdate",
    "AgentVersionResponse",
    "PaginatedResponse",
]


class AgentCreate(BaseModel):
    """Request body for creating an agent."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    framework: str = "deepagents"
    config: dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Request body for updating an agent — creates a new version."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    config: dict[str, Any] | None = None
    change_summary: str | None = None


class AgentVersionResponse(BaseModel):
    """Agent version in API responses."""

    id: UUID
    agent_id: UUID
    version: int
    config: dict[str, Any]
    change_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    """Agent in API responses."""

    id: UUID
    name: str
    description: str | None
    framework: str
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    model: str | None = None
    tools_count: int = 0
    api_key_configured: bool = False

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    items: list[Any]
    total: int
    page: int
    limit: int
