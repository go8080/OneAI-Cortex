"""Pydantic schemas for connected services endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "ConnectedServiceListResponse",
    "ConnectedServiceResponse",
    "GoogleConnectRequest",
    "GoogleScopesResponse",
    "GoogleTokenResponse",
]


class GoogleConnectRequest(BaseModel):
    """Request body for exchanging a Google authorization code."""

    code: str = Field(..., min_length=1, description="Google authorization code")
    redirect_uri: str = Field(
        default="", description="Redirect URI used in OAuth flow"
    )


class ConnectedServiceResponse(BaseModel):
    """Connected service in API responses."""

    id: UUID
    provider: str
    provider_email: str | None
    status: str
    granted_scopes: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GoogleScopesResponse(BaseModel):
    """Google connection status and granted scopes."""

    connected: bool
    scopes: list[str]
    email: str | None


class GoogleTokenResponse(BaseModel):
    """Fresh Google access token for agent runtime."""

    access_token: str
    expires_in: int
    scopes: list[str]


class ConnectedServiceListResponse(BaseModel):
    """List of connected services."""

    items: list[ConnectedServiceResponse]
    total: int
