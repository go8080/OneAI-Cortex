"""Tests for app.services.agent — AgentService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.adapters.registry import AdapterRegistry
from app.core.encryption import SecretEncryption
from app.core.exceptions import AdapterError, AuthorizationError, EntityNotFoundError
from app.services.agent import AgentService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


@pytest.fixture
def adapter_registry():
    registry = AdapterRegistry()
    adapter = MagicMock()
    adapter.framework_name = "deepagents"
    adapter.validate_config = AsyncMock(return_value=MagicMock(valid=True, errors=[], warnings=[]))
    registry.register(adapter)
    return registry


@pytest.fixture
def service(repo, adapter_registry, encryption):
    return AgentService(repo, adapter_registry, encryption)


class TestCreateAgent:
    async def test_creates_agent_and_version(self, service, repo):
        agent = MagicMock(id=uuid4(), current_version=1)
        repo.create.return_value = agent
        repo.create_version.return_value = MagicMock()

        result = await service.create_agent(uuid4(), "My Agent", None, "deepagents", {})
        assert result is agent
        repo.create.assert_called_once()
        repo.create_version.assert_called_once()

    async def test_encrypts_user_api_keys(self, service, repo, encryption):
        agent = MagicMock(id=uuid4(), current_version=1)
        repo.create.return_value = agent
        repo.create_version.return_value = MagicMock()

        config = {"user_api_keys": {"OPENAI_API_KEY": "sk-123"}}
        await service.create_agent(uuid4(), "Agent", None, "deepagents", config)

        version_call = repo.create_version.call_args[0][0]
        # The key should be encrypted (different from original)
        encrypted_key = version_call["config"]["user_api_keys"]["OPENAI_API_KEY"]
        assert encrypted_key != "sk-123"
        # But decryptable
        assert encryption.decrypt(encrypted_key) == "sk-123"

    async def test_invalid_framework_raises(self, service, repo):
        with pytest.raises(AdapterError):
            await service.create_agent(uuid4(), "Agent", None, "nonexistent", {})


class TestGetAgent:
    async def test_returns_agent(self, service, repo, test_user):
        user_id = uuid4()
        agent = MagicMock(user_id=user_id, is_deleted=False)
        repo.get_by_id.return_value = agent

        result = await service.get_agent(uuid4(), user_id)
        assert result is agent

    async def test_raises_if_not_found(self, service, repo):
        repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.get_agent(uuid4(), uuid4())

    async def test_raises_if_wrong_user(self, service, repo):
        agent = MagicMock(user_id=uuid4(), is_deleted=False)
        repo.get_by_id.return_value = agent
        with pytest.raises(AuthorizationError):
            await service.get_agent(uuid4(), uuid4())  # different user


class TestDeleteAgent:
    async def test_soft_deletes(self, service, repo):
        user_id = uuid4()
        agent = MagicMock(user_id=user_id, is_deleted=False)
        repo.get_by_id.return_value = agent
        repo.soft_delete.return_value = True

        await service.delete_agent(agent.id, user_id)
        repo.soft_delete.assert_called_once()
