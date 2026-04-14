"""Domain exceptions. No HTTP awareness — translated to HTTP status in the API layer."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base for all application errors."""

    def __init__(self, message: str, code: str = "UNKNOWN") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class EntityNotFoundError(AppError):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, field: str, value: Any) -> None:
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(f"{entity} with {field}={value} not found", "NOT_FOUND")


class DuplicateEntityError(AppError):
    """Raised when creating an entity that already exists."""

    def __init__(self, entity: str, field: str, value: Any) -> None:
        super().__init__(f"{entity} with {field}={value} already exists", "DUPLICATE")


class AuthenticationError(AppError):
    """Raised when authentication fails (invalid token, expired, etc.)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, "UNAUTHORIZED")


class AuthorizationError(AppError):
    """Raised when user lacks permission for an operation."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, "FORBIDDEN")


class ValidationError(AppError):
    """Raised when domain-level validation fails (beyond Pydantic schema validation)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR")


class EncryptionError(AppError):
    """Raised when encryption/decryption fails (tampered data, missing key)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "ENCRYPTION_ERROR")


class AdapterError(AppError):
    """Raised when a framework adapter encounters an error."""

    def __init__(self, message: str, adapter: str = "unknown") -> None:
        self.adapter = adapter
        super().__init__(message, "ADAPTER_ERROR")


class AgentExecutionError(AppError):
    """Raised when agent execution fails (timeout, LLM error, etc.)."""

    def __init__(self, message: str, agent_id: str | None = None) -> None:
        self.agent_id = agent_id
        super().__init__(message, "EXECUTION_ERROR")


class MCPConnectionError(AppError):
    """Raised when MCP server connectivity fails."""

    def __init__(self, server_name: str, message: str) -> None:
        self.server_name = server_name
        super().__init__(f"MCP server '{server_name}': {message}", "MCP_ERROR")


class ServiceError(AppError):
    """Raised when an external service call fails (Google OAuth, etc.)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "SERVICE_ERROR")
