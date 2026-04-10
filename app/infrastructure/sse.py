"""SSE streaming — converts AgentEvent stream to Server-Sent Events."""

from __future__ import annotations

import json
from typing import AsyncIterator

from app.adapters.types import AgentEvent

__all__ = ["event_to_sse_data", "sse_event_generator"]


def event_to_sse_data(event: AgentEvent) -> str:
    """Serialize an AgentEvent to SSE data format."""
    return json.dumps({
        "type": event.type,
        "content": event.content,
        "metadata": event.metadata,
        "timestamp": event.timestamp.isoformat(),
    })


async def sse_event_generator(
    events: AsyncIterator[AgentEvent],
) -> AsyncIterator[dict[str, str]]:
    """Convert an AgentEvent stream to sse-starlette event dicts."""
    async for event in events:
        yield {
            "event": event.type,
            "data": event_to_sse_data(event),
        }
