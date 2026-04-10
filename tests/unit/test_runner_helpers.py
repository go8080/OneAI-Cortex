"""Tests for runner service helpers — _normalize_model, _build_agent_config."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.adapters.types import (
    AsyncSubAgentConfig,
    BackendConfig,
    InterruptConfig,
    MiddlewareConfig,
    SyncSubAgentConfig,
)
from app.core.encryption import SecretEncryption
from app.services.runner import _build_agent_config, _normalize_model


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


class TestNormalizeModel:
    def test_string_passthrough(self):
        assert _normalize_model("openai:gpt-4o") == "openai:gpt-4o"

    def test_string_with_anthropic(self):
        assert _normalize_model("anthropic:claude-sonnet-4-6") == "anthropic:claude-sonnet-4-6"

    def test_dict_with_provider_and_model_id(self):
        model = {"provider": "openai", "model_id": "gpt-4o", "display_name": "GPT-4o"}
        assert _normalize_model(model) == "openai:gpt-4o"

    def test_dict_anthropic(self):
        model = {"provider": "anthropic", "model_id": "claude-sonnet-4-6", "requires_api_key": "ANTHROPIC_API_KEY"}
        assert _normalize_model(model) == "anthropic:claude-sonnet-4-6"

    def test_dict_missing_provider_falls_back(self):
        model = {"model_id": "gpt-4o"}
        result = _normalize_model(model)
        assert result == "anthropic:claude-sonnet-4-6"  # default fallback

    def test_dict_missing_model_id_falls_back(self):
        model = {"provider": "openai"}
        result = _normalize_model(model)
        assert result == "anthropic:claude-sonnet-4-6"

    def test_empty_dict_falls_back(self):
        result = _normalize_model({})
        assert result == "anthropic:claude-sonnet-4-6"

    def test_invalid_type_falls_back(self):
        result = _normalize_model(12345)
        assert result == "anthropic:claude-sonnet-4-6"

    def test_none_falls_back(self):
        result = _normalize_model(None)
        assert result == "anthropic:claude-sonnet-4-6"


class TestBuildAgentConfig:
    """Tests for _build_agent_config — full config hydration from stored dict."""

    def test_minimal_config_uses_defaults(self, encryption):
        config = _build_agent_config({}, "My Agent", encryption)
        assert config.name == "My Agent"
        assert config.model == "anthropic:claude-sonnet-4-6"
        assert config.system_prompt == ""
        assert config.tools == []
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.recursion_limit == 100
        assert config.checkpointing_enabled is True
        assert config.debug is False
        assert config.subagents == []
        assert config.interrupt_on is None
        assert config.response_format is None
        assert config.framework_specific == {}
        assert isinstance(config.middleware, MiddlewareConfig)
        assert isinstance(config.backend, BackendConfig)

    def test_scalar_fields_populated(self, encryption):
        config = _build_agent_config({
            "model": "openai:gpt-4o",
            "system_prompt": "Be helpful",
            "tools": ["search", "calculator"],
            "mcp_servers": ["filesystem"],
            "temperature": 0.3,
            "max_tokens": 8192,
            "recursion_limit": 50,
            "checkpointing_enabled": False,
            "debug": True,
        }, "Agent", encryption)
        assert config.model == "openai:gpt-4o"
        assert config.system_prompt == "Be helpful"
        assert config.tools == ["search", "calculator"]
        assert config.mcp_servers == ["filesystem"]
        assert config.temperature == 0.3
        assert config.max_tokens == 8192
        assert config.recursion_limit == 50
        assert config.checkpointing_enabled is False
        assert config.debug is True

    def test_model_dict_normalized(self, encryption):
        config = _build_agent_config({
            "model": {"provider": "openai", "model_id": "gpt-4o"},
        }, "Agent", encryption)
        assert config.model == "openai:gpt-4o"

    def test_middleware_config_from_dict(self, encryption):
        config = _build_agent_config({
            "middleware": {
                "todo_list": False,
                "human_in_the_loop": True,
                "prompt_caching": False,
            },
        }, "Agent", encryption)
        assert config.middleware.todo_list is False
        assert config.middleware.human_in_the_loop is True
        assert config.middleware.prompt_caching is False
        # Unspecified fields keep defaults
        assert config.middleware.filesystem is True

    def test_middleware_missing_uses_defaults(self, encryption):
        config = _build_agent_config({}, "Agent", encryption)
        assert config.middleware.todo_list is True
        assert config.middleware.human_in_the_loop is False

    def test_backend_config_from_dict(self, encryption):
        config = _build_agent_config({
            "backend": {"type": "filesystem", "root_dir": "/tmp/agent"},
        }, "Agent", encryption)
        assert config.backend.type == "filesystem"
        assert config.backend.root_dir == "/tmp/agent"

    def test_backend_missing_uses_state_default(self, encryption):
        config = _build_agent_config({}, "Agent", encryption)
        assert config.backend.type == "state"
        assert config.backend.root_dir is None

    def test_response_format_passthrough(self, encryption):
        fmt = {"type": "json_object", "schema": {"answer": "string"}}
        config = _build_agent_config({"response_format": fmt}, "Agent", encryption)
        assert config.response_format == fmt

    def test_framework_specific_passthrough(self, encryption):
        extra = {"custom_flag": True, "timeout": 30}
        config = _build_agent_config({"framework_specific": extra}, "Agent", encryption)
        assert config.framework_specific == extra

    def test_interrupt_on_with_bool_values(self, encryption):
        config = _build_agent_config({
            "interrupt_on": {"dangerous_tool": True, "safe_tool": False},
        }, "Agent", encryption)
        assert config.interrupt_on["dangerous_tool"] is True
        assert config.interrupt_on["safe_tool"] is False

    def test_interrupt_on_with_config_dict(self, encryption):
        config = _build_agent_config({
            "interrupt_on": {
                "delete_file": {"message": "Are you sure?"},
            },
        }, "Agent", encryption)
        interrupt = config.interrupt_on["delete_file"]
        assert isinstance(interrupt, InterruptConfig)
        assert interrupt.message == "Are you sure?"

    def test_interrupt_on_none_stays_none(self, encryption):
        config = _build_agent_config({}, "Agent", encryption)
        assert config.interrupt_on is None

    def test_sync_subagent_parsed(self, encryption):
        config = _build_agent_config({
            "subagents": [{
                "name": "researcher",
                "description": "Research assistant",
                "system_prompt": "You research topics",
                "model": "openai:gpt-4o",
                "tools": ["search"],
            }],
        }, "Agent", encryption)
        assert len(config.subagents) == 1
        sub = config.subagents[0]
        assert isinstance(sub, SyncSubAgentConfig)
        assert sub.name == "researcher"
        assert sub.model == "openai:gpt-4o"
        assert sub.tools == ["search"]

    def test_async_subagent_parsed_with_decrypted_headers(self, encryption):
        # Encrypt headers as they would be stored
        encrypted_headers = encryption.encrypt_dict_values({
            "Authorization": "Bearer sk-secret-123",
        })
        config = _build_agent_config({
            "subagents": [{
                "type": "async",
                "name": "indexer",
                "description": "Background indexer",
                "graph_id": "indexing",
                "url": "http://remote:8080",
                "headers": encrypted_headers,
            }],
        }, "Agent", encryption)
        assert len(config.subagents) == 1
        sub = config.subagents[0]
        assert isinstance(sub, AsyncSubAgentConfig)
        assert sub.name == "indexer"
        assert sub.graph_id == "indexing"
        assert sub.url == "http://remote:8080"
        # Headers should be decrypted
        assert sub.headers["Authorization"] == "Bearer sk-secret-123"

    def test_mixed_subagents_sync_and_async(self, encryption):
        encrypted_headers = encryption.encrypt_dict_values({"X-Api-Key": "secret-key"})
        config = _build_agent_config({
            "subagents": [
                {
                    "name": "researcher",
                    "description": "Sync research agent",
                    "system_prompt": "Research topics",
                    "model": "openai:gpt-4o",
                },
                {
                    "type": "async",
                    "name": "indexer",
                    "description": "Async indexing agent",
                    "graph_id": "index_graph",
                    "url": "http://remote:9000",
                    "headers": encrypted_headers,
                },
                {
                    "name": "writer",
                    "description": "Sync writing agent",
                    "system_prompt": "Write content",
                },
            ],
        }, "Agent", encryption)
        assert len(config.subagents) == 3
        # Order preserved, types correct
        assert isinstance(config.subagents[0], SyncSubAgentConfig)
        assert config.subagents[0].name == "researcher"
        assert isinstance(config.subagents[1], AsyncSubAgentConfig)
        assert config.subagents[1].name == "indexer"
        assert config.subagents[1].headers["X-Api-Key"] == "secret-key"
        assert isinstance(config.subagents[2], SyncSubAgentConfig)
        assert config.subagents[2].name == "writer"

    def test_empty_subagents(self, encryption):
        config = _build_agent_config({"subagents": []}, "Agent", encryption)
        assert config.subagents == []

    def test_sync_subagent_with_interrupt_on(self, encryption):
        config = _build_agent_config({
            "subagents": [{
                "name": "editor",
                "description": "File editor",
                "system_prompt": "Edit files",
                "interrupt_on": {"write_file": True},
            }],
        }, "Agent", encryption)
        sub = config.subagents[0]
        assert isinstance(sub, SyncSubAgentConfig)
        assert sub.interrupt_on["write_file"] is True

    def test_non_dict_subagent_entries_skipped(self, encryption):
        config = _build_agent_config({
            "subagents": ["invalid", 42, None, {"name": "valid", "description": "ok", "system_prompt": "hi"}],
        }, "Agent", encryption)
        assert len(config.subagents) == 1
        assert config.subagents[0].name == "valid"
