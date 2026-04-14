"""Pydantic schemas for runner endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "ChatRequest",
    "MessageResponse",
    "ResumeRequest",
    "SessionCreate",
    "SessionDetailResponse",
    "SessionResponse",
]


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


class MessageResponse(BaseModel):
    """Message in API responses."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="meta")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SessionDetailResponse(SessionResponse):
    """Session with messages for single-session GET."""

    messages: list[MessageResponse] = []


class ChatRequest(BaseModel):
    """Request body for sending a message to an agent."""

    message: str = Field(..., min_length=1)


class ResumeRequest(BaseModel):
    """Request body for resuming after HITL interrupt."""

    approved: bool
    modified_args: dict[str, Any] | None = None
