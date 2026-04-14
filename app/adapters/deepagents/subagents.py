"""Subagent builders — convert config objects to DeepAgents SubAgent/AsyncSubAgent dicts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import re

from app.adapters.types import AsyncSubAgentConfig, SyncSubAgentConfig

# OpenAI message `name` field pattern — same as adapter.sanitize_agent_name
_INVALID_NAME_CHARS = re.compile(r'[\s<|\\/>]+')


def _sanitize_name(name: str) -> str:
    """Sanitize a subagent name for use in LLM message payloads."""
    sanitized = _INVALID_NAME_CHARS.sub("_", name).strip("_")
    return sanitized or "subagent"

__all__ = ["build_subagent_dicts"]


def build_subagent_dicts(
    subagents: list[SyncSubAgentConfig | AsyncSubAgentConfig],
    tool_resolver: Callable[[list[str]], list[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Convert subagent configs to DeepAgents TypedDict-compatible dicts.

    Sync subagents become SubAgent dicts. Tool name strings are resolved
    to BaseTool instances via the provided resolver.
    Async subagents become AsyncSubAgent dicts.

    Args:
        subagents: List of subagent config objects.
        tool_resolver: Callable that converts tool name strings to BaseTool
            instances. If None, tool names are omitted from subagent dicts.
    """
    result: list[dict[str, Any]] = []

    for sub in subagents:
        if isinstance(sub, SyncSubAgentConfig):
            d: dict[str, Any] = {
                "name": _sanitize_name(sub.name),
                "description": sub.description,
                "system_prompt": sub.system_prompt,
            }
            if sub.model is not None:
                d["model"] = sub.model
            if sub.tools and tool_resolver is not None:
                resolved = tool_resolver(sub.tools)
                if resolved:
                    d["tools"] = resolved
            if sub.interrupt_on is not None:
                d["interrupt_on"] = sub.interrupt_on
            result.append(d)

        elif isinstance(sub, AsyncSubAgentConfig):
            d = {
                "name": _sanitize_name(sub.name),
                "description": sub.description,
                "graph_id": sub.graph_id,
            }
            if sub.url is not None:
                d["url"] = sub.url
            if sub.headers:
                d["headers"] = sub.headers
            result.append(d)

    return result
