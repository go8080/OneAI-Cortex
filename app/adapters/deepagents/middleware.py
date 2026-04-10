"""Middleware configuration — maps MiddlewareConfig to create_deep_agent() parameters.

create_deep_agent() builds its own ordered middleware stack internally:
  Base: TodoList → Skills* → Filesystem → SubAgent → Summarization → PatchToolCalls → AsyncSubAgent*
  Tail: PromptCaching → Memory* → HumanInTheLoop*
  (* = conditional, based on subagents/interrupt_on/memory/skills args)

The `middleware` param to create_deep_agent() injects ADDITIONAL user middleware
between the base and tail stacks. For v0.1, we have no custom middleware to add.
"""

from __future__ import annotations

from typing import Any

from app.adapters.types import AgentConfig

__all__ = ["build_extra_middleware"]


def build_extra_middleware(config: AgentConfig) -> list[Any]:
    """Build additional user middleware to inject into create_deep_agent().

    Returns an empty list for v0.1 — all standard middleware is handled
    by create_deep_agent() via its top-level parameters (interrupt_on,
    subagents, backend, skills, memory).
    """
    # Future: custom middleware (e.g., rate limiters, audit loggers) goes here.
    return []
