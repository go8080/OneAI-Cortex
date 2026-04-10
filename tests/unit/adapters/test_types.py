"""Tests for app.adapters.types — AgentConfig, MiddlewareConfig, BackendConfig, etc."""

from __future__ import annotations

from app.adapters.types import (
    AgentConfig,
    AsyncSubAgentConfig,
    BackendConfig,
    MiddlewareConfig,
    ModelSpec,
    SyncSubAgentConfig,
    ValidationResult,
)


class TestAgentConfig:
    def test_defaults(self):
        config = AgentConfig(name="test")
        assert config.name == "test"
        assert config.model == "anthropic:claude-sonnet-4-6"
        assert config.system_prompt == ""
        assert config.tools == []
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.recursion_limit == 100
        assert config.checkpointing_enabled is True
        assert config.debug is False
        assert config.framework_specific == {}

    def test_custom_values(self):
        config = AgentConfig(
            name="research",
            model="openai:gpt-4o",
            system_prompt="Be helpful",
            temperature=0.3,
            max_tokens=1000,
        )
        assert config.model == "openai:gpt-4o"
        assert config.temperature == 0.3


class TestMiddlewareConfig:
    def test_defaults_all_true_except_hitl(self):
        mw = MiddlewareConfig()
        assert mw.todo_list is True
        assert mw.filesystem is True
        assert mw.subagent is True
        assert mw.summarization is True
        assert mw.patch_tool_calls is True
        assert mw.async_subagent is True
        assert mw.prompt_caching is True
        assert mw.human_in_the_loop is False


class TestBackendConfig:
    def test_defaults(self):
        bc = BackendConfig()
        assert bc.type == "state"
        assert bc.root_dir is None
        assert bc.max_file_size_mb == 10

    def test_filesystem(self):
        bc = BackendConfig(type="filesystem", root_dir="/tmp/agent")
        assert bc.type == "filesystem"
        assert bc.root_dir == "/tmp/agent"


class TestModelSpec:
    def test_creation(self):
        spec = ModelSpec("openai", "gpt-4o", "GPT-4o", "OPENAI_API_KEY")
        assert spec.provider == "openai"
        assert spec.model_id == "gpt-4o"


class TestValidationResult:
    def test_valid(self):
        vr = ValidationResult(valid=True, errors=[], warnings=[])
        assert vr.valid is True

    def test_invalid(self):
        vr = ValidationResult(valid=False, errors=["bad model"], warnings=[])
        assert vr.valid is False
        assert len(vr.errors) == 1


class TestSubAgentConfigs:
    def test_sync_subagent(self):
        sa = SyncSubAgentConfig(name="helper", description="helps", system_prompt="be nice")
        assert sa.name == "helper"
        assert sa.model is None

    def test_async_subagent(self):
        aa = AsyncSubAgentConfig(name="remote", description="remote agent", graph_id="graph-1")
        assert aa.graph_id == "graph-1"
        assert aa.headers == {}
