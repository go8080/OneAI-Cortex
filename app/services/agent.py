"""Agent service — business logic for agent CRUD and versioning."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.adapters.registry import AdapterRegistry
from app.core.encryption import SecretEncryption
from app.core.exceptions import AuthorizationError, EntityNotFoundError, ValidationError
from app.repositories.agent import AgentRepository

__all__ = ["AgentService"]


class AgentService:
    """Orchestrates agent builder operations."""

    def __init__(
        self,
        repo: AgentRepository,
        adapter_registry: AdapterRegistry,
        encryption: SecretEncryption,
    ) -> None:
        self._repo = repo
        self._adapters = adapter_registry
        self._encryption = encryption

    async def create_agent(self, user_id: UUID, name: str, description: str | None,
                           framework: str, config: dict[str, Any]) -> object:
        """Create an agent with its first version."""
        # Validate framework exists
        self._adapters.get(framework)

        # Encrypt sensitive config fields
        config = self._encrypt_config_secrets(config)

        agent = await self._repo.create({
            "user_id": user_id,
            "name": name,
            "description": description,
            "framework": framework,
            "current_version": 1,
        })

        await self._repo.create_version({
            "agent_id": agent.id,
            "version": 1,
            "config": config,
            "change_summary": "Initial version",
        })

        return agent

    async def get_agent(self, agent_id: UUID, user_id: UUID) -> object:
        """Get an agent, verifying ownership."""
        agent = await self._repo.get_by_id(agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", agent_id)
        if agent.user_id != user_id:
            raise AuthorizationError("Not your agent")
        return agent

    async def list_agents(self, user_id: UUID, *, page: int = 1, limit: int = 50) -> tuple:
        """List agents with pagination. Returns (agents, total_count)."""
        offset = (page - 1) * limit
        agents = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        total = await self._repo.count_by_user(user_id)
        return agents, total

    async def update_agent(
        self,
        agent_id: UUID,
        user_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        config: dict[str, Any] | None = None,
        change_summary: str | None = None,
    ) -> object:
        """Update an agent. If config changes, creates a new version."""
        agent = await self.get_agent(agent_id, user_id)

        # Update scalar fields
        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if status is not None:
            if status not in ("draft", "active", "archived"):
                raise ValidationError(f"Invalid status: {status}")
            update_data["status"] = status

        # Create new version if config changed
        if config is not None:
            config = self._encrypt_config_secrets(config)
            new_version = agent.current_version + 1
            await self._repo.create_version({
                "agent_id": agent_id,
                "version": new_version,
                "config": config,
                "change_summary": change_summary or f"Version {new_version}",
            })
            update_data["current_version"] = new_version

        if update_data:
            await self._repo.update(agent_id, update_data)

        return await self._repo.get_by_id(agent_id)

    async def delete_agent(self, agent_id: UUID, user_id: UUID) -> None:
        """Soft-delete an agent."""
        await self.get_agent(agent_id, user_id)  # verify ownership
        deleted = await self._repo.soft_delete(agent_id)
        if not deleted:
            raise EntityNotFoundError("Agent", "id", agent_id)

    async def get_version(self, agent_id: UUID, user_id: UUID, version: int) -> object:
        """Get a specific agent version."""
        await self.get_agent(agent_id, user_id)  # verify ownership
        ver = await self._repo.get_version(agent_id, version)
        if ver is None:
            raise EntityNotFoundError("AgentVersion", "version", version)
        return ver

    async def list_versions(self, agent_id: UUID, user_id: UUID, *, page: int = 1, limit: int = 50) -> list:
        """List versions for an agent."""
        await self.get_agent(agent_id, user_id)  # verify ownership
        offset = (page - 1) * limit
        return await self._repo.list_versions(agent_id, offset=offset, limit=limit)

    def _encrypt_config_secrets(self, config: dict[str, Any]) -> dict[str, Any]:
        """Encrypt sensitive fields in agent config."""
        config = dict(config)  # shallow copy
        if "user_api_keys" in config and config["user_api_keys"]:
            config["user_api_keys"] = self._encryption.encrypt_dict_values(
                config["user_api_keys"]
            )
        # Encrypt async subagent headers
        if "subagents" in config:
            for sub in config["subagents"]:
                if isinstance(sub, dict) and sub.get("type") == "async" and sub.get("headers"):
                    sub["headers"] = self._encryption.encrypt_dict_values(sub["headers"])
        return config
