"""MCP server service — business logic for MCP server management."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.adapters.types import MCPServerConfig
from app.core.encryption import SecretEncryption
from app.core.exceptions import AuthorizationError, EntityNotFoundError
from app.infrastructure.mcp_client import MCPClient, MCPTestResult
from app.repositories.mcp_server import McpServerRepository
from app.schemas.mcp_server import MCPServerCreate, MCPServerUpdate

__all__ = ["McpServerService"]


class McpServerService:
    """Orchestrates MCP server operations."""

    def __init__(
        self,
        repo: McpServerRepository,
        encryption: SecretEncryption,
        mcp_client: MCPClient,
    ) -> None:
        self._repo = repo
        self._encryption = encryption
        self._mcp_client = mcp_client

    async def create_server(self, user_id: UUID, data: MCPServerCreate) -> object:
        """Register a new MCP server. Encrypts env vars and auth header."""
        server_data = {
            "user_id": user_id,
            "name": data.name,
            "description": data.description,
            "transport": data.transport,
            "url": data.url,
            "command": data.command,
            "args": data.args,
            "env_vars": self._encryption.encrypt_dict_values(data.env_vars)
            if data.env_vars
            else {},
            "auth_header": self._encryption.encrypt(data.auth_header)
            if data.auth_header
            else None,
        }
        return await self._repo.create(server_data)

    async def get_server(self, server_id: UUID, user_id: UUID) -> object:
        """Get an MCP server, verifying ownership."""
        server = await self._repo.get_by_id(server_id)
        if server is None:
            raise EntityNotFoundError("McpServer", "id", server_id)
        if server.user_id != user_id:
            raise AuthorizationError("Not your MCP server")
        return server

    async def list_servers(self, user_id: UUID) -> list:
        """List all MCP servers for a user."""
        return await self._repo.list_by_user(user_id)

    async def test_server(self, server_id: UUID, user_id: UUID) -> MCPTestResult:
        """Test connectivity and discover tools for an MCP server."""
        server = await self.get_server(server_id, user_id)

        # Decrypt secrets for testing
        env_vars = (
            self._encryption.decrypt_dict_values(server.env_vars)
            if server.env_vars
            else {}
        )
        auth_header = (
            self._encryption.decrypt(server.auth_header)
            if server.auth_header
            else None
        )

        config = MCPServerConfig(
            name=server.name,
            transport=server.transport,
            url=server.url,
            command=server.command,
            args=server.args or [],
            env=env_vars,
            auth_header=auth_header,
        )

        result = await self._mcp_client.test_connection(config)

        # Update server status
        update_data: dict = {
            "status": "healthy" if result.reachable else "unhealthy",
            "last_tested_at": datetime.now(UTC),
        }
        if result.reachable:
            update_data["tools_discovered"] = [
                {"name": t.name, "description": t.description}
                for t in result.tools_discovered
            ]
        await self._repo.update(server_id, update_data)

        return result

    async def delete_server(self, server_id: UUID, user_id: UUID) -> None:
        """Delete an MCP server."""
        deleted = await self._repo.delete(server_id, user_id)
        if not deleted:
            raise EntityNotFoundError("McpServer", "id", server_id)
