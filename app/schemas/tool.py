"""Pydantic schemas for tool endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["ToolCreate", "ToolResponse", "ToolUpdate"]


class ToolCreate(BaseModel):
    """Request body for registering a custom tool."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str
    framework: str = Field(..., max_length=50)
    tool_type: str = "custom"
    schema_def: dict[str, Any] = Field(..., alias="schema")
    auth_config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class ToolUpdate(BaseModel):
    """Request body for updating a tool."""

    description: str | None = None
    schema_def: dict[str, Any] | None = Field(None, alias="schema")
    auth_config: dict[str, Any] | None = None
    is_active: bool | None = None

    model_config = {"populate_by_name": True}


class ToolResponse(BaseModel):
    """Tool in API responses."""

    id: UUID
    name: str
    description: str
    framework: str
    tool_type: str
    schema_def: dict[str, Any] = Field(..., serialization_alias="schema")
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
