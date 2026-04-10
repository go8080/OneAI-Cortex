"""Tests for app.core.events — AgentEvent dataclass."""

from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.types import AgentEvent
from app.core.constants import AgentEventType


class TestAgentEvent:
    def test_default_creation(self):
        event = AgentEvent(type=AgentEventType.MESSAGE, content="hello")
        assert event.type == "message"
        assert event.content == "hello"
        assert event.metadata == {}
        assert isinstance(event.timestamp, datetime)

    def test_with_metadata(self):
        event = AgentEvent(
            type=AgentEventType.TOOL_CALL,
            content="search",
            metadata={"input": {"query": "test"}},
        )
        assert event.metadata["input"]["query"] == "test"

    def test_timestamp_is_utc(self):
        event = AgentEvent(type=AgentEventType.DONE, content="")
        assert event.timestamp.tzinfo is not None

    def test_all_event_types(self):
        for event_type in AgentEventType:
            event = AgentEvent(type=event_type, content="test")
            assert event.type == event_type.value
