"""Tool service — business logic for tool registry operations."""

from __future__ import annotations

from uuid import UUID

from app.core.encryption import SecretEncryption
from app.core.exceptions import DuplicateEntityError, EntityNotFoundError
from app.repositories.tool import ToolRepository
from app.schemas.tool import ToolCreate, ToolUpdate

__all__ = ["ToolService"]


class ToolService:
    """Orchestrates tool registry operations."""

    def __init__(self, repo: ToolRepository, encryption: SecretEncryption) -> None:
        self._repo = repo
        self._encryption = encryption

    async def create_tool(self, data: ToolCreate) -> object:
        """Register a new tool. Encrypts auth_config values."""
        existing = await self._repo.get_by_name(data.name)
        if existing:
            raise DuplicateEntityError("Tool", "name", data.name)

        tool_data = {
            "name": data.name,
            "description": data.description,
            "framework": data.framework,
            "tool_type": data.tool_type,
            "schema_def": data.schema_def,
            "auth_config": self._encryption.encrypt_dict_values(data.auth_config)
            if data.auth_config
            else {},
        }
        return await self._repo.create(tool_data)

    async def get_tool(self, tool_id: UUID) -> object:
        """Get a tool by ID."""
        tool = await self._repo.get_by_id(tool_id)
        if tool is None:
            raise EntityNotFoundError("Tool", "id", tool_id)
        return tool

    async def list_tools(self, *, framework: str | None = None) -> list:
        """List all active tools, optionally filtered by framework."""
        return await self._repo.list_tools(framework=framework)

    async def update_tool(self, tool_id: UUID, data: ToolUpdate) -> object:
        """Update a tool. Encrypts auth_config if provided."""
        update_data = data.model_dump(exclude_unset=True)
        if "auth_config" in update_data and update_data["auth_config"]:
            update_data["auth_config"] = self._encryption.encrypt_dict_values(
                update_data["auth_config"]
            )
        tool = await self._repo.update(tool_id, update_data)
        if tool is None:
            raise EntityNotFoundError("Tool", "id", tool_id)
        return tool
