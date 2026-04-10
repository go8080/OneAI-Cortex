"""Pydantic schemas for API key endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["APIKeyCreate", "APIKeyResponse", "APIKeySummary"]


class APIKeyCreate(BaseModel):
    """Request body for creating a new API key."""

    name: str = Field(..., min_length=1, max_length=100)


class APIKeyResponse(BaseModel):
    """Response returned once on creation — includes the raw key."""

    id: UUID
    name: str
    key: str  # raw key — shown once, never again
    key_prefix: str
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeySummary(BaseModel):
    """Response for listing API keys — no raw key, prefix only."""

    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
