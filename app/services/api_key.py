"""API key service — business logic for key creation, listing, and revocation."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import EntityNotFoundError
from app.core.security import generate_api_key
from app.repositories.api_key import ApiKeyRepository
from app.schemas.api_key import APIKeyCreate

__all__ = ["ApiKeyService"]


class ApiKeyService:
    """Orchestrates API key operations. No HTTP or SQL awareness."""

    def __init__(self, repo: ApiKeyRepository) -> None:
        self._repo = repo

    async def create_api_key(self, user_id: UUID, data: APIKeyCreate) -> tuple:
        """Create a new API key. Returns (ApiKey model, raw_key string)."""
        raw_key, key_hash, key_prefix = generate_api_key()
        api_key = await self._repo.create(
            {
                "user_id": user_id,
                "name": data.name,
                "key_hash": key_hash,
                "key_prefix": key_prefix,
            }
        )
        return api_key, raw_key

    async def list_api_keys(self, user_id: UUID) -> list:
        """List all API keys for a user."""
        return await self._repo.list_by_user(user_id)

    async def revoke_api_key(self, user_id: UUID, key_id: UUID) -> None:
        """Revoke an API key. Raises if not found or not owned by user."""
        revoked = await self._repo.revoke(key_id, user_id)
        if not revoked:
            raise EntityNotFoundError("ApiKey", "id", key_id)
