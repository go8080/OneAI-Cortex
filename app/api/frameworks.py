"""Framework endpoints — list registered adapters and their capabilities."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.exceptions import EntityNotFoundError
from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user
from app.schemas.framework import AdapterInfoResponse, ModelSpecResponse

router = APIRouter()


def _get_registry(request: Request):
    """Get the adapter registry from app state."""
    return request.app.state.adapter_registry


@router.get("", response_model=list[AdapterInfoResponse])
async def list_frameworks(
    request: Request,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> list[AdapterInfoResponse]:
    """List all registered framework adapters with version info."""
    registry = _get_registry(request)
    result = []
    for name in registry.list_adapters():
        adapter = registry.get(name)
        result.append(
            AdapterInfoResponse(
                framework_name=adapter.framework_name,
                adapter_version=adapter.adapter_version,
                sdk_compatibility=adapter.sdk_compatibility,
                supported_models=[
                    ModelSpecResponse(
                        provider=m.provider,
                        model_id=m.model_id,
                        display_name=m.display_name,
                        requires_api_key=m.requires_api_key,
                    )
                    for m in adapter.supported_models
                ],
            )
        )
    return result


@router.get("/{name}", response_model=AdapterInfoResponse)
async def get_framework(
    name: str,
    request: Request,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> AdapterInfoResponse:
    """Get details for a specific framework adapter."""
    registry = _get_registry(request)
    try:
        adapter = registry.get(name)
    except Exception:
        raise EntityNotFoundError("Framework", "name", name)

    return AdapterInfoResponse(
        framework_name=adapter.framework_name,
        adapter_version=adapter.adapter_version,
        sdk_compatibility=adapter.sdk_compatibility,
        supported_models=[
            ModelSpecResponse(
                provider=m.provider,
                model_id=m.model_id,
                display_name=m.display_name,
                requires_api_key=m.requires_api_key,
            )
            for m in adapter.supported_models
        ],
    )
