"""Pydantic schemas for MCP server endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["MCPServerCreate", "MCPServerResponse", "MCPServerUpdate", "MCPTestResultResponse"]


class MCPServerCreate(BaseModel):
    """Request body for registering an MCP server."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    transport: str = Field(..., pattern="^(stdio|sse|http)$")
    url: str | None = None
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)
    auth_header: str | None = None


class MCPServerUpdate(BaseModel):
    """Request body for updating an MCP server."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env_vars: dict[str, str] | None = None
    auth_header: str | None = None


class MCPServerResponse(BaseModel):
    """MCP server in API responses. Secrets are masked."""

    id: UUID
    name: str
    description: str | None
    transport: str
    url: str | None
    command: str | None
    args: list[Any]
    status: str
    last_tested_at: datetime | None
    tools_discovered: list[Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPTestResultResponse(BaseModel):
    """Result of testing an MCP server connection."""

    reachable: bool
    tools_discovered: list[dict[str, Any]]
    error: str | None = None
    latency_ms: int
