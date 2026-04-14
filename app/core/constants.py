"""Domain enums and constants. Used across layers — ORM columns, API schemas, service logic."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AgentEventType",
    "AgentStatus",
    "BackendType",
    "ConnectionStatus",
    "DeploymentStatus",
    "ToolAuthType",
    "DeploymentType",
    "EvalRunStatus",
    "FrameworkType",
    "MCPStatus",
    "MCPTransport",
    "MessageRole",
    "ScoringMethod",
    "ServiceProvider",
    "ToolCategory",
    "ToolTestStatus",
    "ToolType",
]


class AgentStatus(StrEnum):
    """Lifecycle status of an agent definition."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConnectionStatus(StrEnum):
    """Status of a connected external service."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


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


class ServiceProvider(StrEnum):
    """Supported external service providers for connected services."""

    GOOGLE = "google"
    SLACK = "slack"
    GITHUB = "github"


class ToolAuthType(StrEnum):
    """How a tool authenticates — determines token source at runtime."""

    API_KEY = "api_key"
    GOOGLE_OAUTH = "google_oauth"
    NONE = "none"


class ToolCategory(StrEnum):
    """Pre-defined tool categories for the built-in catalog."""

    SEARCH = "search"
    RESEARCH = "research"
    BROWSER = "browser"
    COMMUNICATION = "communication"
    DEVTOOLS = "devtools"
    FILES = "files"
    DATABASE = "database"
    DATA_ANALYSIS = "data_analysis"
    SPEECH_AUDIO = "speech_audio"
    IMAGE_VISION = "image_vision"
    DOCUMENTS = "documents"
    MODERATION = "moderation"
    WEATHER_LOCATION = "weather_location"
    FINANCE = "finance"
    TRAVEL = "travel"
    MEDIA = "media"
    SCIENCE = "science"
    AUTOMATION = "automation"
    BLOCKCHAIN = "blockchain"
    UTILITY = "utility"


class ToolTestStatus(StrEnum):
    """Status of the last tool test execution."""

    UNTESTED = "untested"
    SUCCESS = "success"
    FAILED = "failed"


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
