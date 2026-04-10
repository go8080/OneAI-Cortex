"""Tests for infrastructure modules — SSE, auth_client, checkpointer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.types import AgentEvent
from app.core.constants import AgentEventType
from app.infrastructure.sse import event_to_sse_data, sse_event_generator


class TestEventToSseData:
    def test_serializes_event(self):
        event = AgentEvent(type=AgentEventType.MESSAGE, content="hello")
        result = event_to_sse_data(event)
        data = json.loads(result)
        assert data["type"] == "message"
        assert data["content"] == "hello"
        assert "timestamp" in data

    def test_includes_metadata(self):
        event = AgentEvent(
            type=AgentEventType.TOOL_CALL,
            content="search",
            metadata={"input": {"q": "test"}},
        )
        result = event_to_sse_data(event)
        data = json.loads(result)
        assert data["metadata"]["input"]["q"] == "test"

    def test_done_event(self):
        event = AgentEvent(type=AgentEventType.DONE, content="")
        result = event_to_sse_data(event)
        data = json.loads(result)
        assert data["type"] == "done"

    def test_error_event(self):
        event = AgentEvent(type=AgentEventType.ERROR, content="something broke")
        result = event_to_sse_data(event)
        data = json.loads(result)
        assert data["type"] == "error"
        assert data["content"] == "something broke"


class TestSseEventGenerator:
    async def test_generates_sse_dicts(self):
        events = [
            AgentEvent(type=AgentEventType.MESSAGE, content="hi"),
            AgentEvent(type=AgentEventType.DONE, content=""),
        ]

        async def mock_stream():
            for e in events:
                yield e

        results = []
        async for sse_dict in sse_event_generator(mock_stream()):
            results.append(sse_dict)

        assert len(results) == 2
        assert results[0]["event"] == "message"
        assert results[1]["event"] == "done"
        # data should be valid JSON
        for r in results:
            json.loads(r["data"])


class TestAuthClient:
    async def test_health_check_success(self):
        from app.infrastructure.auth_client import AuthClient

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.auth_client.httpx.AsyncClient", return_value=mock_client):
            client = AuthClient(base_url="http://test")
            result = await client.health_check()
            assert result is True

    async def test_health_check_failure(self):
        import httpx

        from app.infrastructure.auth_client import AuthClient

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.infrastructure.auth_client.httpx.AsyncClient", return_value=mock_client):
            client = AuthClient(base_url="http://test")
            result = await client.health_check()
            assert result is False
