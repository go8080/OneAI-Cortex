"""Framework adapter protocol — the contract every adapter must satisfy."""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol

from app.adapters.types import (
    AgentConfig,
    AgentEvent,
    AgentRuntime,
    MCPServerConfig,
    ModelSpec,
    SDKPackage,
    ToolSpec,
    ValidationResult,
)

__all__ = ["FrameworkAdapter"]


class FrameworkAdapter(Protocol):
    """Interface that every framework adapter must implement."""

    @property
    def framework_name(self) -> str: ...

    @property
    def adapter_version(self) -> str: ...

    @property
    def sdk_compatibility(self) -> str: ...

    @property
    def supported_models(self) -> list[ModelSpec]: ...

    async def validate_config(self, config: AgentConfig) -> ValidationResult: ...

    async def create_runtime(
        self, config: AgentConfig, user_api_keys: dict[str, str]
    ) -> AgentRuntime: ...

    async def execute(
        self,
        runtime: AgentRuntime,
        messages: list[dict[str, str]],
        session_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]: ...

    async def generate_sdk_package(self, config: AgentConfig) -> SDKPackage: ...

    def get_available_tools(self) -> list[ToolSpec]: ...

    async def attach_mcp_servers(
        self, runtime: AgentRuntime, mcp_configs: list[MCPServerConfig]
    ) -> None: ...

    async def resume_after_interrupt(
        self,
        runtime: AgentRuntime,
        session_id: str,
        approved: bool,
        modified_args: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentEvent]: ...
