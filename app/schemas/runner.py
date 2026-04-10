"""Pydantic schemas for runner endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["ChatRequest", "ResumeRequest", "SessionCreate", "SessionResponse"]


class SessionCreate(BaseModel):
    """Request body to create a new session."""

    agent_id: UUID
    title: str | None = None


class SessionResponse(BaseModel):
    """Session in API responses."""

    id: UUID
    agent_id: UUID
    agent_version: int
    title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """Request body for sending a message to an agent."""

    message: str = Field(..., min_length=1)


class ResumeRequest(BaseModel):
    """Request body for resuming after HITL interrupt."""

    approved: bool
    modified_args: dict[str, Any] | None = None
