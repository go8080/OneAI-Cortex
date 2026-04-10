"""Pydantic schemas for deployer endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

__all__ = ["DeployRequest", "DeploymentResponse"]


class DeployRequest(BaseModel):
    """Request body for deploying an agent."""

    type: str  # "hosted" or "sdk_download"
    agent_version: int | None = None  # None = use current_version


class DeploymentResponse(BaseModel):
    """Deployment in API responses."""

    id: UUID
    agent_id: UUID
    agent_version: int
    type: str
    status: str
    endpoint_url: str | None
    download_count: int
    created_at: datetime
    stopped_at: datetime | None

    model_config = {"from_attributes": True}
