"""Pydantic schemas for framework endpoints."""

from __future__ import annotations

from pydantic import BaseModel

__all__ = ["AdapterInfoResponse", "ModelSpecResponse"]


class ModelSpecResponse(BaseModel):
    """A supported model specification."""

    provider: str
    model_id: str
    display_name: str
    requires_api_key: str


class AdapterInfoResponse(BaseModel):
    """Information about a registered framework adapter."""

    framework_name: str
    adapter_version: str
    sdk_compatibility: str
    supported_models: list[ModelSpecResponse]
