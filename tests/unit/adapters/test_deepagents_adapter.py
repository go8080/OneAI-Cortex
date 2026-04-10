"""Tests for DeepAgents adapter — sanitize_agent_name, validate_config, backends, subagents, middleware."""

from __future__ import annotations

import pytest

from app.adapters.deepagents.adapter import sanitize_agent_name
from app.adapters.deepagents.backends import build_backend
from app.adapters.deepagents.middleware import build_extra_middleware
from app.adapters.deepagents.subagents import build_subagent_dicts
from app.adapters.types import (
    AgentConfig,
    AsyncSubAgentConfig,
    BackendConfig,
    SyncSubAgentConfig,
)


class TestSanitizeAgentName:
    def test_spaces_replaced(self):
        assert sanitize_agent_name("My Research Agent") == "My_Research_Agent"

    def test_special_chars_replaced(self):
        assert sanitize_agent_name("agent<test>") == "agent_test"

    def test_slashes_replaced(self):
        result = sanitize_agent_name("a/b")
        assert "/" not in result

    def test_pipe_replaced(self):
        result = sanitize_agent_name("a|b")
        assert "|" not in result

    def test_backslash_replaced(self):
        result = sanitize_agent_name("a\\b")
        assert "\\" not in result

    def test_clean_name_unchanged(self):
        assert sanitize_agent_name("simple_agent") == "simple_agent"

    def test_empty_string_returns_agent(self):
        assert sanitize_agent_name("") == "agent"

    def test_only_spaces_returns_agent(self):
        assert sanitize_agent_name("   ") == "agent"

    def test_leading_trailing_stripped(self):
        assert sanitize_agent_name("  hello  ") == "hello"

    def test_multiple_consecutive_spaces(self):
        result = sanitize_agent_name("my   agent")
        assert "  " not in result


class TestBuildBackend:
    def test_state_backend(self):
        config = BackendConfig(type="state")
        backend = build_backend(config)
        assert backend is not None

    def test_filesystem_backend(self):
        config = BackendConfig(type="filesystem", root_dir="/tmp/test")
        backend = build_backend(config)
        assert backend is not None

    def test_filesystem_without_root_dir_raises(self):
        config = BackendConfig(type="filesystem", root_dir=None)
        with pytest.raises(ValueError, match="root_dir"):
            build_backend(config)


class TestBuildExtraMiddleware:
    def test_returns_empty_list(self):
        config = AgentConfig(name="test")
        result = build_extra_middleware(config)
        assert result == []


class TestBuildSubagentDicts:
    def test_empty_list(self):
        assert build_subagent_dicts([]) == []

    def test_sync_subagent(self):
        configs = [SyncSubAgentConfig(name="helper", description="helps", system_prompt="be nice")]
        result = build_subagent_dicts(configs)
        assert len(result) == 1
        assert result[0]["name"] == "helper"
        assert result[0]["description"] == "helps"
        assert result[0]["system_prompt"] == "be nice"

    def test_async_subagent(self):
        configs = [AsyncSubAgentConfig(name="remote", description="remote", graph_id="g1", url="http://localhost:9000")]
        result = build_subagent_dicts(configs)
        assert len(result) == 1
        assert result[0]["graph_id"] == "g1"
        assert result[0]["url"] == "http://localhost:9000"

    def test_mixed_subagents(self):
        configs = [
            SyncSubAgentConfig(name="sync", description="s", system_prompt="sp"),
            AsyncSubAgentConfig(name="async", description="a", graph_id="g2"),
        ]
        result = build_subagent_dicts(configs)
        assert len(result) == 2
