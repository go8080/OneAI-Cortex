"""API key endpoints — create, list, revoke."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.repositories.api_key import ApiKeyRepository
from app.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeySummary
from app.services.api_key import ApiKeyService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(db))


@router.post("", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ApiKeyService = Depends(_get_service),
) -> APIKeyResponse:
    """Create a new API key. The raw key is returned once — store it securely."""
    api_key, raw_key = await service.create_api_key(user.user_id, body)
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[APIKeySummary])
async def list_api_keys(
    user: AuthenticatedUser = Depends(get_current_user),
    service: ApiKeyService = Depends(_get_service),
) -> list[APIKeySummary]:
    """List all API keys for the authenticated user."""
    keys = await service.list_api_keys(user.user_id)
    return [APIKeySummary.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ApiKeyService = Depends(_get_service),
) -> None:
    """Revoke an API key."""
    await service.revoke_api_key(user.user_id, key_id)
