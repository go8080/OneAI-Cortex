"""Tests for app.core.constants — StrEnum definitions."""

from __future__ import annotations

from enum import StrEnum

from app.core.constants import (
    AgentEventType,
    AgentStatus,
    BackendType,
    DeploymentStatus,
    DeploymentType,
    EvalRunStatus,
    FrameworkType,
    MCPStatus,
    MCPTransport,
    MessageRole,
    ScoringMethod,
    ToolType,
)


class TestAllEnumsAreStrEnum:
    ENUMS = [
        AgentStatus, FrameworkType, DeploymentType, DeploymentStatus,
        MCPTransport, MCPStatus, EvalRunStatus, ScoringMethod,
        MessageRole, ToolType, BackendType, AgentEventType,
    ]

    def test_all_are_str_enum(self):
        for enum_cls in self.ENUMS:
            assert issubclass(enum_cls, StrEnum), f"{enum_cls.__name__} is not StrEnum"

    def test_all_values_are_strings(self):
        for enum_cls in self.ENUMS:
            for member in enum_cls:
                assert isinstance(member.value, str)


class TestSpecificValues:
    def test_agent_status_values(self):
        assert AgentStatus.DRAFT == "draft"
        assert AgentStatus.ACTIVE == "active"
        assert AgentStatus.ARCHIVED == "archived"

    def test_framework_type(self):
        assert FrameworkType.DEEPAGENTS == "deepagents"

    def test_mcp_transport(self):
        assert set(MCPTransport) >= {MCPTransport.STDIO, MCPTransport.SSE, MCPTransport.HTTP}

    def test_scoring_method(self):
        assert ScoringMethod.EXACT_MATCH == "exact_match"
        assert ScoringMethod.CONTAINS == "contains"
        assert ScoringMethod.LLM_JUDGE == "llm_judge"

    def test_agent_event_type(self):
        assert AgentEventType.MESSAGE == "message"
        assert AgentEventType.TOOL_CALL == "tool_call"
        assert AgentEventType.DONE == "done"
        assert AgentEventType.ERROR == "error"

    def test_message_role(self):
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"

    def test_deployment_type(self):
        assert DeploymentType.HOSTED == "hosted"
        assert DeploymentType.SDK_DOWNLOAD == "sdk_download"

    def test_json_serialization(self):
        """StrEnum values serialize naturally to JSON strings."""
        import json
        data = {"status": AgentStatus.DRAFT}
        result = json.dumps(data)
        assert '"draft"' in result
