"""Runner service — orchestrates agent execution with session management."""

from __future__ import annotations

from typing import Any, AsyncIterator
from uuid import UUID

import structlog

from app.adapters.registry import AdapterRegistry
from app.adapters.types import (
    AgentConfig,
    AgentEvent,
    AsyncSubAgentConfig,
    BackendConfig,
    InterruptConfig,
    MiddlewareConfig,
    SyncSubAgentConfig,
)
from app.core.encryption import SecretEncryption
from app.core.exceptions import EntityNotFoundError
from app.repositories.agent import AgentRepository
from app.repositories.session import SessionRepository

__all__ = ["RunnerService"]

logger = structlog.get_logger(__name__)


class RunnerService:
    """Orchestrates agent execution — session lifecycle, config loading, adapter dispatch."""

    def __init__(
        self,
        session_repo: SessionRepository,
        agent_repo: AgentRepository,
        adapter_registry: AdapterRegistry,
        encryption: SecretEncryption,
    ) -> None:
        self._sessions = session_repo
        self._agents = agent_repo
        self._adapters = adapter_registry
        self._encryption = encryption

    async def create_session(self, agent_id: UUID, user_id: UUID, title: str | None = None) -> object:
        """Create a new chat session for an agent."""
        agent = await self._agents.get_by_id(agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", agent_id)

        return await self._sessions.create_session({
            "agent_id": agent_id,
            "user_id": user_id,
            "agent_version": agent.current_version,
            "title": title,
        })

    async def run_session(
        self, session_id: UUID, user_id: UUID, message: str
    ) -> AsyncIterator[AgentEvent]:
        """Send a message to an agent session and stream events."""
        session = await self._sessions.get_session(session_id)
        if session is None:
            raise EntityNotFoundError("Session", "id", session_id)

        # Load agent + version config
        agent = await self._agents.get_by_id(session.agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", session.agent_id)

        version = await self._agents.get_version(session.agent_id, session.agent_version)
        if version is None:
            raise EntityNotFoundError("AgentVersion", "version", session.agent_version)

        config_dict = version.config

        # Decrypt user API keys (passed separately to create_runtime)
        user_api_keys = {}
        if config_dict.get("user_api_keys"):
            user_api_keys = self._encryption.decrypt_dict_values(config_dict["user_api_keys"])

        # Build full AgentConfig from stored config
        agent_config = _build_agent_config(config_dict, agent.name, self._encryption)

        # Get adapter and create runtime
        adapter = self._adapters.get(agent.framework)
        runtime = await adapter.create_runtime(agent_config, user_api_keys)

        # Set up checkpointing
        if agent_config.checkpointing_enabled:
            runtime.session_id = str(session_id)

        # Store user message
        await self._sessions.add_message({
            "session_id": session_id,
            "role": "user",
            "content": message,
        })

        # Build message history
        messages = await self._sessions.get_messages(session_id)
        message_dicts = [{"role": m.role, "content": m.content} for m in messages]

        # Execute and stream
        full_response = ""
        async for event in adapter.execute(runtime, message_dicts, str(session_id)):
            if event.type == "message":
                full_response += event.content
            yield event

        # Store assistant response
        if full_response:
            await self._sessions.add_message({
                "session_id": session_id,
                "role": "assistant",
                "content": full_response,
            })

    async def resume_session(
        self, session_id: UUID, user_id: UUID, approved: bool,
        modified_args: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Resume a session after HITL interrupt."""
        session = await self._sessions.get_session(session_id)
        if session is None:
            raise EntityNotFoundError("Session", "id", session_id)

        agent = await self._agents.get_by_id(session.agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", session.agent_id)

        version = await self._agents.get_version(session.agent_id, session.agent_version)
        if version is None:
            raise EntityNotFoundError("AgentVersion", "version", session.agent_version)

        config_dict = version.config

        # Decrypt user API keys (passed separately to create_runtime)
        user_api_keys = {}
        if config_dict.get("user_api_keys"):
            user_api_keys = self._encryption.decrypt_dict_values(config_dict["user_api_keys"])

        # Build full AgentConfig — must match run_session for consistent behavior
        agent_config = _build_agent_config(config_dict, agent.name, self._encryption)
        adapter = self._adapters.get(agent.framework)
        runtime = await adapter.create_runtime(agent_config, user_api_keys)

        async for event in adapter.resume_after_interrupt(
            runtime, str(session_id), approved, modified_args
        ):
            yield event


def _normalize_model(model_raw: str | dict) -> str:
    """Convert model field to 'provider:model_id' string.

    Accepts either:
      - str: "openai:gpt-4o" (pass-through)
      - dict: {"provider": "openai", "model_id": "gpt-4o", ...} → "openai:gpt-4o"
    """
    if isinstance(model_raw, str):
        return model_raw

    if isinstance(model_raw, dict):
        provider = model_raw.get("provider", "")
        model_id = model_raw.get("model_id", "")
        if provider and model_id:
            return f"{provider}:{model_id}"

    logger.warning("runner.invalid_model_format", model_raw=str(model_raw)[:200])
    return "anthropic:claude-sonnet-4-6"


def _build_agent_config(
    config_dict: dict[str, Any],
    agent_name: str,
    encryption: SecretEncryption,
) -> AgentConfig:
    """Hydrate a full AgentConfig from a stored version config dict.

    Converts nested dicts to typed dataclasses (MiddlewareConfig, BackendConfig,
    SyncSubAgentConfig, AsyncSubAgentConfig) and decrypts async subagent headers.
    Missing fields fall back to AgentConfig defaults.

    Args:
        config_dict: The JSONB config blob from AgentVersion.config.
        agent_name: The agent's display name (from Agent.name).
        encryption: Encryption service for decrypting async subagent headers.

    Returns:
        A fully populated AgentConfig ready for adapter consumption.
    """
    # --- Model ---
    model = _normalize_model(config_dict.get("model", "anthropic:claude-sonnet-4-6"))

    # --- Middleware ---
    middleware_raw = config_dict.get("middleware")
    middleware = MiddlewareConfig(**middleware_raw) if isinstance(middleware_raw, dict) else MiddlewareConfig()

    # --- Backend ---
    backend_raw = config_dict.get("backend")
    backend = BackendConfig(**backend_raw) if isinstance(backend_raw, dict) else BackendConfig()

    # --- Subagents ---
    subagents = _parse_subagents(config_dict.get("subagents", []), encryption)

    # --- Interrupt config ---
    interrupt_on = _parse_interrupt_on(config_dict.get("interrupt_on"))

    return AgentConfig(
        name=agent_name,
        model=model,
        system_prompt=config_dict.get("system_prompt", ""),
        tools=config_dict.get("tools", []),
        mcp_servers=config_dict.get("mcp_servers", []),
        subagents=subagents,
        middleware=middleware,
        response_format=config_dict.get("response_format"),
        temperature=config_dict.get("temperature", 0.7),
        max_tokens=config_dict.get("max_tokens", 4096),
        recursion_limit=config_dict.get("recursion_limit", 100),
        backend=backend,
        interrupt_on=interrupt_on,
        checkpointing_enabled=config_dict.get("checkpointing_enabled", True),
        debug=config_dict.get("debug", False),
        framework_specific=config_dict.get("framework_specific", {}),
    )


def _parse_subagents(
    subagents_raw: list[dict[str, Any]],
    encryption: SecretEncryption,
) -> list[SyncSubAgentConfig | AsyncSubAgentConfig]:
    """Parse subagent dicts into typed config objects.

    Detects async subagents by the presence of ``"type": "async"`` and decrypts
    their headers. All others are treated as sync subagents.
    """
    result: list[SyncSubAgentConfig | AsyncSubAgentConfig] = []

    for sub in subagents_raw:
        if not isinstance(sub, dict):
            continue

        if sub.get("type") == "async":
            headers = sub.get("headers", {})
            if headers:
                headers = encryption.decrypt_dict_values(headers)
            result.append(AsyncSubAgentConfig(
                name=sub.get("name", "async_agent"),
                description=sub.get("description", ""),
                graph_id=sub.get("graph_id", ""),
                url=sub.get("url"),
                headers=headers,
            ))
        else:
            interrupt_on = _parse_interrupt_on(sub.get("interrupt_on"))
            result.append(SyncSubAgentConfig(
                name=sub.get("name", "subagent"),
                description=sub.get("description", ""),
                system_prompt=sub.get("system_prompt", ""),
                model=sub.get("model"),
                tools=sub.get("tools"),
                interrupt_on=interrupt_on,
            ))

    return result


def _parse_interrupt_on(
    raw: dict[str, Any] | None,
) -> dict[str, bool | InterruptConfig] | None:
    """Parse interrupt_on dict, converting nested dicts to InterruptConfig."""
    if raw is None:
        return None

    result: dict[str, bool | InterruptConfig] = {}
    for tool_name, value in raw.items():
        if isinstance(value, dict):
            result[tool_name] = InterruptConfig(**value)
        else:
            result[tool_name] = bool(value)
    return result
