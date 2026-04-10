"""Tests for app.services.tool — ToolService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.core.encryption import SecretEncryption
from app.core.exceptions import DuplicateEntityError, EntityNotFoundError
from app.schemas.tool import ToolCreate
from app.services.tool import ToolService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


@pytest.fixture
def service(repo, encryption):
    return ToolService(repo, encryption)


class TestCreateTool:
    async def test_creates_tool(self, service, repo):
        repo.get_by_name.return_value = None
        repo.create.return_value = MagicMock(id=uuid4(), name="web_search")

        data = ToolCreate(name="web_search", description="Search", framework="deepagents", schema_def={"type": "function"})
        result = await service.create_tool(data)
        repo.create.assert_called_once()

    async def test_duplicate_name_raises(self, service, repo):
        repo.get_by_name.return_value = MagicMock()
        data = ToolCreate(name="existing", description="x", framework="deepagents", schema_def={})
        with pytest.raises(DuplicateEntityError):
            await service.create_tool(data)

    async def test_encrypts_auth_config(self, service, repo, encryption):
        repo.get_by_name.return_value = None
        repo.create.return_value = MagicMock()

        data = ToolCreate(
            name="authed_tool", description="x", framework="deepagents",
            schema_def={}, auth_config={"api_key": "secret123"},
        )
        await service.create_tool(data)
        call_data = repo.create.call_args[0][0]
        assert call_data["auth_config"]["api_key"] != "secret123"


class TestGetTool:
    async def test_returns_tool(self, service, repo):
        tool = MagicMock()
        repo.get_by_id.return_value = tool
        result = await service.get_tool(uuid4())
        assert result is tool

    async def test_raises_if_not_found(self, service, repo):
        repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.get_tool(uuid4())


class TestListTools:
    async def test_lists_all(self, service, repo):
        repo.list_tools.return_value = [MagicMock(), MagicMock()]
        result = await service.list_tools()
        assert len(result) == 2

    async def test_filters_by_framework(self, service, repo):
        repo.list_tools.return_value = [MagicMock()]
        await service.list_tools(framework="deepagents")
        repo.list_tools.assert_called_once_with(framework="deepagents")
