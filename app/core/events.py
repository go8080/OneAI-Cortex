"""Domain events emitted during agent execution, streamed to clients via SSE."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.constants import AgentEventType

__all__ = ["AgentEvent"]


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """Single event emitted during an agent run.

    For interrupt events, metadata must include:
        tool_name: str — the tool that triggered the interrupt
        tool_args: dict — arguments passed to the tool
        interrupt_message: str — message shown to the user
    """

    type: AgentEventType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
