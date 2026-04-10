"""Shared types used by the adapter protocol and all adapter implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from app.core.constants import AgentEventType

__all__ = [
    "AdapterVersionInfo",
    "AgentConfig",
    "AgentEvent",
    "AgentRuntime",
    "AsyncSubAgentConfig",
    "BackendConfig",
    "InterruptConfig",
    "MCPServerConfig",
    "MCPTestResult",
    "MiddlewareConfig",
    "ModelSpec",
    "SDKPackage",
    "SyncSubAgentConfig",
    "ToolSpec",
    "ValidationResult",
]


# === Agent Configuration ===


@dataclass
class MiddlewareConfig:
    """Toggles for the DeepAgents middleware stack."""

    todo_list: bool = True
    filesystem: bool = True
    subagent: bool = True
    summarization: bool = True
    patch_tool_calls: bool = True
    async_subagent: bool = True
    prompt_caching: bool = True
    human_in_the_loop: bool = False


@dataclass
class BackendConfig:
    """Backend selection for file operations within agent execution."""

    type: Literal["state", "filesystem"] = "state"
    root_dir: str | None = None
    max_file_size_mb: int = 10


@dataclass
class InterruptConfig:
    """Detailed interrupt configuration for a specific tool."""

    message: str = "Approval required"


@dataclass
class SyncSubAgentConfig:
    """Sync subagent — runs in-process, blocks parent until done."""

    name: str
    description: str
    system_prompt: str
    model: str | None = None
    tools: list[str] | None = None
    interrupt_on: dict[str, bool | InterruptConfig] | None = None


@dataclass
class AsyncSubAgentConfig:
    """Async subagent — runs on remote Agent Protocol server."""

    name: str
    description: str
    graph_id: str
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """Framework-agnostic agent configuration. Maps to create_deep_agent() parameters."""

    name: str
    model: str = "anthropic:claude-sonnet-4-6"
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    subagents: list[SyncSubAgentConfig | AsyncSubAgentConfig] = field(default_factory=list)
    middleware: MiddlewareConfig = field(default_factory=MiddlewareConfig)
    response_format: dict[str, Any] | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    recursion_limit: int = 100
    backend: BackendConfig = field(default_factory=BackendConfig)
    interrupt_on: dict[str, bool | InterruptConfig] | None = None
    checkpointing_enabled: bool = True
    debug: bool = False
    framework_specific: dict[str, Any] = field(default_factory=dict)
    user_api_keys: dict[str, str] = field(default_factory=dict)


# === Runtime & Events ===


@dataclass
class AgentRuntime:
    """Opaque handle to a ready-to-execute agent."""

    runtime_id: str
    framework: str
    session_id: str | None = None
    _internal: Any = None


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Streaming event from agent execution."""

    type: AgentEventType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# === MCP ===


@dataclass
class MCPServerConfig:
    """Configuration for connecting to an MCP server."""

    name: str
    transport: Literal["stdio", "sse", "http"]
    url: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    auth_header: str | None = None


@dataclass
class MCPTestResult:
    """Result of testing MCP server connectivity."""

    reachable: bool
    tools_discovered: list[ToolSpec] = field(default_factory=list)
    error: str | None = None
    latency_ms: int = 0


# === Metadata ===


@dataclass
class ModelSpec:
    """Supported model specification."""

    provider: str
    model_id: str
    display_name: str
    requires_api_key: str


@dataclass
class ToolSpec:
    """Tool specification provided by a framework."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterVersionInfo:
    """Version metadata for a framework adapter."""

    adapter_name: str
    adapter_version: str
    sdk_name: str
    sdk_version_installed: str
    sdk_compatibility: str
    compatible: bool


@dataclass
class ValidationResult:
    """Result of config validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SDKPackage:
    """Generated SDK artifact for download."""

    filename: str
    content: bytes
    dependencies: list[str] = field(default_factory=list)
    python_version: str = "3.11"
    instructions: str = ""
