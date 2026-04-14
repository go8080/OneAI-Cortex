"""Pydantic schemas for tool endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "ToolCategoryResponse",
    "ToolCreate",
    "ToolResponse",
    "ToolTestRequest",
    "ToolTestResponse",
    "ToolUpdate",
]


class ToolCreate(BaseModel):
    """Request body for registering a custom tool."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str
    framework: str = Field(..., max_length=50)
    tool_type: str = "custom"
    category: str | None = None
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
    category: str | None = None
    schema_def: dict[str, Any] = Field(..., serialization_alias="schema")
    is_active: bool
    auth_type: str = "api_key"
    required_keys: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    test_status: str = "untested"
    last_tested_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ToolTestRequest(BaseModel):
    """Request body for tool playground test."""

    api_keys: dict[str, str] = Field(
        ..., description="API keys required by the tool"
    )
    input: dict[str, Any] = Field(
        ..., description="Query and parameters for the tool"
    )


class ToolTestResponse(BaseModel):
    """Response from tool playground test."""

    status: str = Field(..., description="Test result: success or failed")
    output: Any | None = None
    error: str | None = None
    latency_ms: int = Field(..., description="Execution time in milliseconds")


class ToolCategoryResponse(BaseModel):
    """Category with tool count."""

    name: str
    display_name: str
    tool_count: int
