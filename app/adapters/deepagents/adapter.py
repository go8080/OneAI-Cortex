"""DeepAgents framework adapter — implements the FrameworkAdapter protocol."""

from __future__ import annotations

import os
import re
import uuid
from typing import Any, AsyncIterator

import structlog

from app.adapters.deepagents.backends import build_backend
from app.adapters.deepagents.middleware import build_extra_middleware
from app.adapters.deepagents.models import resolve_model
from app.adapters.deepagents.subagents import build_subagent_dicts
from app.adapters.deepagents.tools import resolve_tools
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
from app.core.constants import AgentEventType
from app.core.exceptions import AdapterError, AgentExecutionError

__all__ = ["DeepAgentsAdapter", "sanitize_agent_name"]

logger = structlog.get_logger(__name__)

# OpenAI message `name` field pattern: no whitespace, <, |, \, /, >
_INVALID_NAME_CHARS = re.compile(r'[\s<|\\/>]+')


def sanitize_agent_name(name: str) -> str:
    """Sanitize agent name for use in LLM message payloads.

    OpenAI requires message `name` to match ^[^\\s<|\\\\/>]+$.
    Replaces invalid characters with underscores, strips leading/trailing underscores.
    """
    sanitized = _INVALID_NAME_CHARS.sub("_", name).strip("_")
    return sanitized or "agent"

ADAPTER_VERSION = "1.0.0"
SDK_COMPATIBILITY = ">=0.5.0,<1.0.0"


class DeepAgentsAdapter:
    """Adapter for the DeepAgents framework by LangChain.

    Maps AgentConfig to create_deep_agent() calls and translates
    execution events to framework-agnostic AgentEvent stream.
    """

    @property
    def framework_name(self) -> str:
        return "deepagents"

    @property
    def adapter_version(self) -> str:
        return ADAPTER_VERSION

    @property
    def sdk_compatibility(self) -> str:
        return SDK_COMPATIBILITY

    @property
    def supported_models(self) -> list[ModelSpec]:
        return [
            ModelSpec("anthropic", "claude-sonnet-4-6", "Claude Sonnet 4.6", "ANTHROPIC_API_KEY"),
            ModelSpec("anthropic", "claude-opus-4-6", "Claude Opus 4.6", "ANTHROPIC_API_KEY"),
            ModelSpec("anthropic", "claude-haiku-4-5-20251001", "Claude Haiku 4.5", "ANTHROPIC_API_KEY"),
            ModelSpec("openai", "gpt-4o", "GPT-4o", "OPENAI_API_KEY"),
            ModelSpec("openai", "gpt-4o-mini", "GPT-4o Mini", "OPENAI_API_KEY"),
            ModelSpec("google_genai", "gemini-2.0-flash", "Gemini 2.0 Flash", "GOOGLE_API_KEY"),
        ]

    async def validate_config(self, config: AgentConfig) -> ValidationResult:
        """Validate an agent config before saving."""
        errors: list[str] = []
        warnings: list[str] = []

        # Validate model format
        if ":" not in config.model:
            errors.append(f"Invalid model '{config.model}' — expected 'provider:model' format")

        # Validate backend
        if config.backend.type == "filesystem" and not config.backend.root_dir:
            errors.append("FilesystemBackend requires 'root_dir' to be set")

        # Warn on debug mode
        if config.debug:
            warnings.append("Debug mode is enabled — disable for production")

        # Validate recursion limit
        if config.recursion_limit < 1:
            errors.append("recursion_limit must be >= 1")

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    async def create_runtime(
        self,
        config: AgentConfig,
        user_api_keys: dict[str, str],
        *,
        google_access_token: str | None = None,
    ) -> AgentRuntime:
        """Build a runnable agent from config. Does NOT execute it."""
        from deepagents import create_deep_agent

        # Set API keys as environment variables for this execution
        env_backup: dict[str, str | None] = {}
        for key_name, key_value in user_api_keys.items():
            env_backup[key_name] = os.environ.get(key_name)
            os.environ[key_name] = key_value

        try:
            model = resolve_model(
                config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            extra_middleware = build_extra_middleware(config)
            backend = build_backend(config.backend)

            # Resolve tool name strings → BaseTool instances
            # Google OAuth tools get a fresh access token; regular tools use env vars
            top_level_tools = resolve_tools(
                config.tools, google_access_token=google_access_token
            ) if config.tools else []
            subagents = build_subagent_dicts(config.subagents, resolve_tools)

            # When using the default in-memory backend, file tools produce
            # phantom sandbox:/ links the user can't access.  Append a guard
            # so the agent responds inline instead.
            system_prompt = config.system_prompt
            if config.backend.type == "state":
                guard = (
                    "\n\nIMPORTANT: You are running in a chat environment without "
                    "a filesystem sandbox. Do NOT use file tools (write_file, "
                    "read_file, edit_file, ls, glob, grep) or the execute tool. "
                    "Do NOT generate download links or sandbox:/ paths. "
                    "Always respond directly in the conversation with your full "
                    "answer — never tell the user to download a file."
                )
                system_prompt = (system_prompt or "") + guard

            # Build create_deep_agent kwargs — the framework handles
            # its own middleware stack; we pass top-level knobs directly.
            kwargs: dict[str, Any] = {
                "model": model,
                "system_prompt": system_prompt,
                "backend": backend,
                "name": sanitize_agent_name(config.name),
                "debug": config.debug,
            }

            if top_level_tools:
                kwargs["tools"] = top_level_tools

            if extra_middleware:
                kwargs["middleware"] = extra_middleware

            if subagents:
                kwargs["subagents"] = subagents

            if config.interrupt_on:
                kwargs["interrupt_on"] = config.interrupt_on

            if config.response_format:
                kwargs["response_format"] = config.response_format

            # Framework-specific escape hatch
            kwargs.update(config.framework_specific)

            graph = create_deep_agent(**kwargs)

            runtime_id = str(uuid.uuid4())
            return AgentRuntime(
                runtime_id=runtime_id,
                framework="deepagents",
                _internal=graph,
            )
        except Exception as exc:
            raise AdapterError(
                f"Failed to create agent runtime: {exc}", adapter="deepagents"
            ) from exc
        finally:
            # Restore original env vars
            for key_name, original in env_backup.items():
                if original is None:
                    os.environ.pop(key_name, None)
                else:
                    os.environ[key_name] = original

    async def execute(
        self,
        runtime: AgentRuntime,
        messages: list[dict[str, str]],
        session_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Execute agent with messages, yielding streaming events."""
        graph = runtime._internal
        if graph is None:
            raise AgentExecutionError("Runtime has no internal graph", agent_id=runtime.runtime_id)

        config: dict[str, Any] = {}
        if session_id:
            config["configurable"] = {"thread_id": session_id}

        try:
            # Stream events from LangGraph
            async for event in graph.astream_events(
                {"messages": messages}, config=config, version="v2"
            ):
                kind = event.get("event", "")
                data = event.get("data", {})

                if kind == "on_chat_model_stream":
                    chunk = data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield AgentEvent(
                            type=AgentEventType.MESSAGE,
                            content=chunk.content,
                        )

                elif kind == "on_tool_start":
                    tool_run_id = event.get("run_id", "")
                    yield AgentEvent(
                        type=AgentEventType.TOOL_CALL,
                        content=event.get("name", "unknown_tool"),
                        metadata={
                            "tool_call_id": tool_run_id,
                            "tool_name": event.get("name", "unknown_tool"),
                            "tool_args": data.get("input", {}),
                        },
                    )

                elif kind == "on_tool_end":
                    tool_run_id = event.get("run_id", "")
                    output = data.get("output", "")
                    yield AgentEvent(
                        type=AgentEventType.TOOL_RESULT,
                        content=str(output),
                        metadata={
                            "tool_call_id": tool_run_id,
                            "tool_name": event.get("name", ""),
                        },
                    )

            yield AgentEvent(type=AgentEventType.DONE, content="")

        except Exception as exc:
            logger.error("deepagents.execution_error", error=str(exc), runtime_id=runtime.runtime_id)
            yield AgentEvent(
                type=AgentEventType.ERROR,
                content=str(exc),
            )

    async def generate_sdk_package(self, config: AgentConfig) -> SDKPackage:
        """Generate a standalone SDK package for this agent."""
        # SDK generation will be fully implemented in T33
        raise NotImplementedError("SDK generation not yet implemented")

    def get_available_tools(self) -> list[ToolSpec]:
        """Return tools provided by DeepAgents out of the box."""
        # Tool discovery from the framework will be implemented in T21
        return []

    async def attach_mcp_servers(
        self, runtime: AgentRuntime, mcp_configs: list[MCPServerConfig]
    ) -> None:
        """Attach MCP servers to an agent runtime before execution."""
        # MCP attachment will be implemented in T22
        pass

    async def resume_after_interrupt(
        self,
        runtime: AgentRuntime,
        session_id: str,
        approved: bool,
        modified_args: dict[str, Any] | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Resume execution after HITL interrupt."""
        graph = runtime._internal
        if graph is None:
            raise AgentExecutionError("Runtime has no internal graph")

        config = {"configurable": {"thread_id": session_id}}

        try:
            if approved:
                # Resume with original or modified args
                input_data = modified_args if modified_args else None
                async for event in graph.astream_events(
                    input_data, config=config, version="v2"
                ):
                    kind = event.get("event", "")
                    data = event.get("data", {})

                    if kind == "on_chat_model_stream":
                        chunk = data.get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            yield AgentEvent(
                                type=AgentEventType.MESSAGE,
                                content=chunk.content,
                            )
                    elif kind == "on_tool_end":
                        yield AgentEvent(
                            type=AgentEventType.TOOL_RESULT,
                            content=str(data.get("output", "")),
                        )

                yield AgentEvent(type=AgentEventType.DONE, content="")
            else:
                # Rejected — skip the tool call and notify
                yield AgentEvent(
                    type=AgentEventType.MESSAGE,
                    content="Tool call was rejected by user.",
                )
                yield AgentEvent(type=AgentEventType.DONE, content="")

        except Exception as exc:
            logger.error("deepagents.resume_error", error=str(exc))
            yield AgentEvent(type=AgentEventType.ERROR, content=str(exc))
