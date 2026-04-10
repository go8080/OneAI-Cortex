"""Tests for app.services.mcp_server — McpServerService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.core.encryption import SecretEncryption
from app.core.exceptions import AuthorizationError, EntityNotFoundError
from app.services.mcp_server import McpServerService
from app.schemas.mcp_server import MCPServerCreate


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


@pytest.fixture
def mcp_client():
    return AsyncMock()


@pytest.fixture
def service(repo, encryption, mcp_client):
    return McpServerService(repo, encryption, mcp_client)


class TestCreateServer:
    async def test_creates_server(self, service, repo):
        repo.create.return_value = MagicMock(id=uuid4())
        data = MCPServerCreate(name="fs-tools", transport="stdio", command="npx", args=["-y", "server"])
        result = await service.create_server(uuid4(), data)
        repo.create.assert_called_once()

    async def test_encrypts_env_vars(self, service, repo, encryption):
        repo.create.return_value = MagicMock()
        data = MCPServerCreate(name="remote", transport="sse", url="http://localhost:3001", env_vars={"SECRET": "val123"})
        await service.create_server(uuid4(), data)
        call_data = repo.create.call_args[0][0]
        assert call_data["env_vars"]["SECRET"] != "val123"

    async def test_encrypts_auth_header(self, service, repo, encryption):
        repo.create.return_value = MagicMock()
        data = MCPServerCreate(name="remote", transport="http", url="http://x", auth_header="Bearer token123")
        await service.create_server(uuid4(), data)
        call_data = repo.create.call_args[0][0]
        assert call_data["auth_header"] != "Bearer token123"


class TestGetServer:
    async def test_returns_server(self, service, repo):
        user_id = uuid4()
        server = MagicMock(user_id=user_id)
        repo.get_by_id.return_value = server
        result = await service.get_server(uuid4(), user_id)
        assert result is server

    async def test_raises_if_not_found(self, service, repo):
        repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.get_server(uuid4(), uuid4())

    async def test_raises_if_wrong_user(self, service, repo):
        server = MagicMock(user_id=uuid4())
        repo.get_by_id.return_value = server
        with pytest.raises(AuthorizationError):
            await service.get_server(uuid4(), uuid4())


class TestDeleteServer:
    async def test_deletes(self, service, repo):
        user_id = uuid4()
        server = MagicMock(user_id=user_id)
        repo.get_by_id.return_value = server
        await service.delete_server(uuid4(), user_id)
        repo.delete.assert_called_once()
