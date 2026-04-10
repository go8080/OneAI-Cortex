"""Subagent builders — convert config objects to DeepAgents SubAgent/AsyncSubAgent dicts."""

from __future__ import annotations

from typing import Any

from app.adapters.types import AsyncSubAgentConfig, SyncSubAgentConfig

__all__ = ["build_subagent_dicts"]


def build_subagent_dicts(
    subagents: list[SyncSubAgentConfig | AsyncSubAgentConfig],
) -> list[dict[str, Any]]:
    """Convert subagent configs to DeepAgents TypedDict-compatible dicts.

    Sync subagents become SubAgent dicts.
    Async subagents become AsyncSubAgent dicts.
    """
    result: list[dict[str, Any]] = []

    for sub in subagents:
        if isinstance(sub, SyncSubAgentConfig):
            d: dict[str, Any] = {
                "name": sub.name,
                "description": sub.description,
                "system_prompt": sub.system_prompt,
            }
            if sub.model is not None:
                d["model"] = sub.model
            if sub.tools is not None:
                d["tools"] = sub.tools
            if sub.interrupt_on is not None:
                d["interrupt_on"] = sub.interrupt_on
            result.append(d)

        elif isinstance(sub, AsyncSubAgentConfig):
            d = {
                "name": sub.name,
                "description": sub.description,
                "graph_id": sub.graph_id,
            }
            if sub.url is not None:
                d["url"] = sub.url
            if sub.headers:
                d["headers"] = sub.headers
            result.append(d)

    return result
