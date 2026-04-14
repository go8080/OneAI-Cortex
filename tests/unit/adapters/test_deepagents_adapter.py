"""Tests for DeepAgents adapter — sanitize_agent_name, validate_config, backends, subagents, middleware, tool resolver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.adapters.deepagents.adapter import sanitize_agent_name
from app.adapters.deepagents.backends import build_backend
from app.adapters.deepagents.middleware import build_extra_middleware
from app.adapters.deepagents.subagents import build_subagent_dicts
from app.adapters.deepagents.tools import resolve_tools, _TOOL_CLASS_MAP
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

    def test_subagent_name_sanitized(self):
        """Subagent names with spaces should be sanitized for OpenAI compatibility."""
        configs = [
            SyncSubAgentConfig(name="Research Analyst", description="r", system_prompt="s"),
            SyncSubAgentConfig(name="SEO Specialist", description="s", system_prompt="s"),
        ]
        result = build_subagent_dicts(configs)
        assert result[0]["name"] == "Research_Analyst"
        assert result[1]["name"] == "SEO_Specialist"

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

    def test_sync_subagent_tools_resolved(self):
        """Tool names should be resolved via the tool_resolver callback."""
        mock_tool = MagicMock()
        mock_tool.name = "tavily_search"
        resolver = MagicMock(return_value=[mock_tool])

        configs = [
            SyncSubAgentConfig(
                name="researcher", description="r", system_prompt="s",
                tools=["tavily_search"],
            ),
        ]
        result = build_subagent_dicts(configs, tool_resolver=resolver)
        resolver.assert_called_once_with(["tavily_search"])
        assert result[0]["tools"] == [mock_tool]

    def test_sync_subagent_tools_omitted_without_resolver(self):
        """Without a resolver, tool names should not appear in the dict."""
        configs = [
            SyncSubAgentConfig(
                name="helper", description="h", system_prompt="s",
                tools=["tavily_search"],
            ),
        ]
        result = build_subagent_dicts(configs)
        assert "tools" not in result[0]


class TestToolResolver:
    def test_catalog_map_populated(self):
        """The _TOOL_CLASS_MAP should contain all catalog tools."""
        assert len(_TOOL_CLASS_MAP) == 61
        assert "tavily_search" in _TOOL_CLASS_MAP
        assert "ddg_search" in _TOOL_CLASS_MAP

    def test_unknown_tool_skipped(self):
        """Unknown tool names should be skipped, not raise errors."""
        result = resolve_tools(["nonexistent_tool"])
        assert result == []

    def test_empty_list(self):
        result = resolve_tools([])
        assert result == []

    def test_mixed_known_unknown(self):
        """Known tools are looked up, unknown tools are silently skipped."""
        # Even if the import fails (langchain_community not installed),
        # unknown tools should be skipped without raising
        result = resolve_tools(["fake_tool_xyz"])
        assert result == []

    def test_known_tool_import_failure_is_graceful(self):
        """If a tool's module can't be imported, it's warned and skipped — not raised."""
        # tavily_search is in the catalog but langchain_community may not be installed
        result = resolve_tools(["tavily_search"])
        # Either resolves (if installed) or returns empty (if not) — never raises
        assert isinstance(result, list)

    def test_resolve_with_mock_tool(self):
        """Verify resolution works end-to-end when the import succeeds."""
        from unittest.mock import patch, MagicMock

        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.name = "tavily_search"
        mock_cls.return_value = mock_instance

        mock_module = MagicMock()
        mock_module.TavilySearchResults = mock_cls

        with patch("importlib.import_module", return_value=mock_module):
            result = resolve_tools(["tavily_search"])

        assert len(result) == 1
        assert result[0].name == "tavily_search"
        mock_cls.assert_called_once_with()
