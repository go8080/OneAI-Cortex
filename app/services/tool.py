"""Tool service — business logic for tool registry, categories, and playground."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.adapters.deepagents.tool_instantiation import (
    GOOGLE_OAUTH_TOOLS,
    instantiate_google_oauth_tools,
    instantiate_tool,
)
from app.core.constants import ToolAuthType
from app.core.encryption import SecretEncryption
from app.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.repositories.tool import ToolRepository
from app.schemas.tool import (
    ToolCategoryResponse,
    ToolCreate,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)

__all__ = ["ToolService"]

_TOOL_TEST_TIMEOUT_SECONDS = 30


class ToolService:
    """Orchestrates tool registry, category browsing, and playground testing."""

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
            "category": data.category,
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

    async def list_tools(
        self,
        *,
        framework: str | None = None,
        category: str | None = None,
    ) -> list:
        """List all active tools, optionally filtered by framework and/or category."""
        return await self._repo.list_tools(framework=framework, category=category)

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

    async def list_categories(self) -> list[ToolCategoryResponse]:
        """Return all tool categories with their tool counts."""
        rows = await self._repo.list_categories()
        return [
            ToolCategoryResponse(
                name=name,
                display_name=name.replace("_", " ").title(),
                tool_count=count,
            )
            for name, count in rows
        ]

    async def test_tool(
        self,
        tool_id: UUID,
        request: ToolTestRequest,
        *,
        google_access_token: str | None = None,
    ) -> ToolTestResponse:
        """Execute a tool with user-provided API keys and input (playground).

        Instantiates the LangChain tool dynamically, invokes it with the
        user's input via ainvoke(), and returns the actual output or error.

        For google_oauth tools, a fresh Google access token must be provided
        (fetched from Connected Services by the API layer).
        """
        tool = await self._repo.get_by_id(tool_id)
        if tool is None:
            raise EntityNotFoundError("Tool", "id", tool_id)

        if not tool.langchain_class:
            raise ValidationError(
                "Playground is only available for built-in tools with a LangChain class"
            )

        # Google OAuth tools require a connected Google account, not API keys
        is_google_oauth = getattr(tool, "auth_type", "api_key") == ToolAuthType.GOOGLE_OAUTH

        if is_google_oauth and not google_access_token:
            raise ValidationError(
                "This tool requires a connected Google account. "
                "Go to Connected Services to link your Google account."
            )

        # Validate required API keys are present (only for non-google-oauth tools)
        if not is_google_oauth:
            missing_keys = [
                key for key in (tool.required_keys or []) if key not in request.api_keys
            ]
            if missing_keys:
                raise ValidationError(
                    f"Missing required API keys: {', '.join(missing_keys)}"
                )

        start = time.monotonic()
        try:
            if is_google_oauth:
                # Google OAuth tools use access token, not env vars
                google_tools = instantiate_google_oauth_tools(
                    [tool.name], google_access_token
                )
                if not google_tools:
                    raise ValidationError(f"Failed to instantiate Google tool: {tool.name}")
                tool_instance = google_tools[0]
            else:
                # Regular tools — use shared wrapper-aware instantiation
                tool_instance = instantiate_tool(
                    tool.name,
                    api_keys=request.api_keys,
                    set_env=True,
                )
            output = await tool_instance.ainvoke(request.input)
            latency_ms = int((time.monotonic() - start) * 1000)

            detail = {
                "output": _serialize_output(output),
                "latency_ms": latency_ms,
                "tested_at": datetime.now(UTC).isoformat(),
                "input_used": request.input,
            }
            await self._repo.update_test_result(
                tool_id, status="success", detail=detail, tested_at=datetime.now(UTC)
            )
            return ToolTestResponse(
                status="success",
                output=_serialize_output(output),
                error=None,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            error_msg = f"{type(exc).__name__}: {exc}"

            detail = {
                "error": error_msg,
                "latency_ms": latency_ms,
                "tested_at": datetime.now(UTC).isoformat(),
                "input_used": request.input,
            }
            await self._repo.update_test_result(
                tool_id, status="failed", detail=detail, tested_at=datetime.now(UTC)
            )
            return ToolTestResponse(
                status="failed",
                output=None,
                error=error_msg,
                latency_ms=latency_ms,
            )


def _serialize_output(output: Any) -> Any:
    """Ensure tool output is JSON-serializable for storage in JSONB."""
    if isinstance(output, str):
        return output
    if isinstance(output, (list, dict, int, float, bool, type(None))):
        return output
    return str(output)
