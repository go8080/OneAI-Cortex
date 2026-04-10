"""Domain enums and constants. Used across layers — ORM columns, API schemas, service logic."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AgentEventType",
    "AgentStatus",
    "BackendType",
    "DeploymentStatus",
    "DeploymentType",
    "EvalRunStatus",
    "FrameworkType",
    "MCPStatus",
    "MCPTransport",
    "MessageRole",
    "ScoringMethod",
    "ToolType",
]


class AgentStatus(StrEnum):
    """Lifecycle status of an agent definition."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class FrameworkType(StrEnum):
    """Supported agent frameworks."""

    DEEPAGENTS = "deepagents"
    CREWAI = "crewai"
    AUTOGEN = "autogen"


class DeploymentType(StrEnum):
    """How an agent is deployed to consumers."""

    HOSTED = "hosted"
    SDK_DOWNLOAD = "sdk_download"


class DeploymentStatus(StrEnum):
    """Runtime status of a deployment."""

    ACTIVE = "active"
    STOPPED = "stopped"
    EXPIRED = "expired"


class MCPTransport(StrEnum):
    """MCP server connection transport."""

    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class MCPStatus(StrEnum):
    """Health status of an MCP server connection."""

    UNTESTED = "untested"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class EvalRunStatus(StrEnum):
    """Status of an evaluation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringMethod(StrEnum):
    """How test case results are scored."""

    EXACT_MATCH = "exact_match"
    CONTAINS = "contains"
    LLM_JUDGE = "llm_judge"


class MessageRole(StrEnum):
    """Role of a message in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ToolType(StrEnum):
    """Origin of a tool definition."""

    BUILTIN = "builtin"
    CUSTOM = "custom"


class BackendType(StrEnum):
    """Agent execution backend type."""

    STATE = "state"
    FILESYSTEM = "filesystem"


class AgentEventType(StrEnum):
    """Types of events emitted during agent execution via SSE."""

    MESSAGE = "message"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    INTERRUPT = "interrupt"
    DONE = "done"
