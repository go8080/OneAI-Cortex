"""Tests for app.services.api_key — ApiKeyService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import EntityNotFoundError
from app.schemas.api_key import APIKeyCreate
from app.services.api_key import ApiKeyService


@pytest.fixture
def repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(repo):
    return ApiKeyService(repo)


class TestCreateApiKey:
    async def test_returns_model_and_raw_key(self, service, repo):
        repo.create.return_value = MagicMock(id=uuid4(), name="test-key", key_prefix="ctx_ab")
        data = APIKeyCreate(name="test-key")
        result, raw_key = await service.create_api_key(uuid4(), data)
        assert raw_key.startswith("ctx_")
        repo.create.assert_called_once()

    async def test_passes_user_id_to_repo(self, service, repo):
        repo.create.return_value = MagicMock()
        user_id = uuid4()
        await service.create_api_key(user_id, APIKeyCreate(name="k"))
        call_args = repo.create.call_args[0][0]
        assert call_args["user_id"] == user_id


class TestListApiKeys:
    async def test_delegates_to_repo(self, service, repo):
        repo.list_by_user.return_value = [MagicMock(), MagicMock()]
        result = await service.list_api_keys(uuid4())
        assert len(result) == 2


class TestRevokeApiKey:
    async def test_revokes_existing_key(self, service, repo):
        repo.revoke.return_value = True
        await service.revoke_api_key(uuid4(), uuid4())
        repo.revoke.assert_called_once()

    async def test_raises_if_not_found(self, service, repo):
        repo.revoke.return_value = False
        with pytest.raises(EntityNotFoundError):
            await service.revoke_api_key(uuid4(), uuid4())
