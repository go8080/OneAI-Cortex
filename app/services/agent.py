"""Agent service — business logic for agent CRUD and versioning."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.adapters.registry import AdapterRegistry
from app.core.encryption import SecretEncryption
from app.core.exceptions import (
    AuthorizationError,
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.models.agent import Agent
from app.repositories.agent import AgentRepository
from app.schemas.agent import AgentResponse

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
                           framework: str, config: dict[str, Any]) -> AgentResponse:
        """Create an agent with its first version."""
        # Validate framework exists
        self._adapters.get(framework)

        # Enforce unique name per user
        if await self._repo.name_exists_for_user(user_id, name):
            raise DuplicateEntityError("Agent", "name", name)

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

        return await self._enrich_agent(agent)

    async def get_agent(self, agent_id: UUID, user_id: UUID) -> AgentResponse:
        """Get an agent, verifying ownership."""
        agent = await self._get_agent_raw(agent_id, user_id)
        return await self._enrich_agent(agent)

    async def _get_agent_raw(self, agent_id: UUID, user_id: UUID) -> Agent:
        """Get the raw ORM agent, verifying ownership."""
        agent = await self._repo.get_by_id(agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", agent_id)
        if agent.user_id != user_id:
            raise AuthorizationError("Not your agent")
        return agent

    async def list_agents(self, user_id: UUID, *, page: int = 1, limit: int = 50) -> tuple:
        """List agents with pagination. Returns (enriched agents, total_count)."""
        offset = (page - 1) * limit
        agents = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        total = await self._repo.count_by_user(user_id)
        enriched = [await self._enrich_agent(a) for a in agents]
        return enriched, total

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
    ) -> AgentResponse:
        """Update an agent. If config changes, creates a new version."""
        agent = await self._get_agent_raw(agent_id, user_id)

        # Update scalar fields
        update_data: dict[str, Any] = {}
        if name is not None:
            if name != agent.name and await self._repo.name_exists_for_user(
                user_id, name, exclude_id=agent_id
            ):
                raise DuplicateEntityError("Agent", "name", name)
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

        updated = await self._repo.get_by_id(agent_id)
        return await self._enrich_agent(updated)

    async def delete_agent(self, agent_id: UUID, user_id: UUID) -> None:
        """Soft-delete an agent."""
        await self._get_agent_raw(agent_id, user_id)  # verify ownership
        deleted = await self._repo.soft_delete(agent_id)
        if not deleted:
            raise EntityNotFoundError("Agent", "id", agent_id)

    async def get_version(self, agent_id: UUID, user_id: UUID, version: int) -> object:
        """Get a specific agent version."""
        await self._get_agent_raw(agent_id, user_id)  # verify ownership
        ver = await self._repo.get_version(agent_id, version)
        if ver is None:
            raise EntityNotFoundError("AgentVersion", "version", version)
        return ver

    async def list_versions(self, agent_id: UUID, user_id: UUID, *, page: int = 1, limit: int = 50) -> list:
        """List versions for an agent."""
        await self._get_agent_raw(agent_id, user_id)  # verify ownership
        offset = (page - 1) * limit
        return await self._repo.list_versions(agent_id, offset=offset, limit=limit)

    async def _enrich_agent(self, agent: Agent) -> AgentResponse:
        """Build an AgentResponse with model/tools/api_key info from latest version."""
        version = await self._repo.get_latest_version(agent.id)
        model: str | None = None
        tools_count = 0
        api_key_configured = False

        if version and version.config:
            cfg = version.config
            model = cfg.get("model")
            tools_count = len(cfg.get("tools") or [])
            api_key_configured = bool(cfg.get("user_api_keys"))

        base = AgentResponse.model_validate(agent, from_attributes=True)
        base.model = model
        base.tools_count = tools_count
        base.api_key_configured = api_key_configured
        return base

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
