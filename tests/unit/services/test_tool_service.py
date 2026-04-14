"""Tests for app.services.tool — ToolService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.core.encryption import SecretEncryption
from app.core.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ValidationError,
)
from app.schemas.tool import ToolCreate, ToolTestRequest
from app.services.tool import ToolService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


@pytest.fixture
def service(repo, encryption):
    return ToolService(repo, encryption)


class TestCreateTool:
    async def test_creates_tool(self, service, repo):
        repo.get_by_name.return_value = None
        repo.create.return_value = MagicMock(id=uuid4(), name="web_search")

        data = ToolCreate(name="web_search", description="Search", framework="deepagents", schema_def={"type": "function"})
        result = await service.create_tool(data)
        repo.create.assert_called_once()

    async def test_duplicate_name_raises(self, service, repo):
        repo.get_by_name.return_value = MagicMock()
        data = ToolCreate(name="existing", description="x", framework="deepagents", schema_def={})
        with pytest.raises(DuplicateEntityError):
            await service.create_tool(data)

    async def test_encrypts_auth_config(self, service, repo, encryption):
        repo.get_by_name.return_value = None
        repo.create.return_value = MagicMock()

        data = ToolCreate(
            name="authed_tool", description="x", framework="deepagents",
            schema_def={}, auth_config={"api_key": "secret123"},
        )
        await service.create_tool(data)
        call_data = repo.create.call_args[0][0]
        assert call_data["auth_config"]["api_key"] != "secret123"


class TestGetTool:
    async def test_returns_tool(self, service, repo):
        tool = MagicMock()
        repo.get_by_id.return_value = tool
        result = await service.get_tool(uuid4())
        assert result is tool

    async def test_raises_if_not_found(self, service, repo):
        repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.get_tool(uuid4())


class TestListTools:
    async def test_lists_all(self, service, repo):
        repo.list_tools.return_value = [MagicMock(), MagicMock()]
        result = await service.list_tools()
        assert len(result) == 2

    async def test_filters_by_framework(self, service, repo):
        repo.list_tools.return_value = [MagicMock()]
        await service.list_tools(framework="deepagents")
        repo.list_tools.assert_called_once_with(framework="deepagents", category=None)

    async def test_filters_by_category(self, service, repo):
        repo.list_tools.return_value = [MagicMock()]
        await service.list_tools(category="search")
        repo.list_tools.assert_called_once_with(framework=None, category="search")

    async def test_filters_by_framework_and_category(self, service, repo):
        repo.list_tools.return_value = []
        await service.list_tools(framework="langchain", category="browser")
        repo.list_tools.assert_called_once_with(framework="langchain", category="browser")


class TestListCategories:
    async def test_returns_categories(self, service, repo):
        repo.list_categories.return_value = [("search", 5), ("browser", 3)]
        result = await service.list_categories()
        assert len(result) == 2
        assert result[0].name == "search"
        assert result[0].display_name == "Search"
        assert result[0].tool_count == 5
        assert result[1].name == "browser"
        assert result[1].display_name == "Browser"

    async def test_returns_empty_list(self, service, repo):
        repo.list_categories.return_value = []
        result = await service.list_categories()
        assert result == []

    async def test_display_name_formatting(self, service, repo):
        repo.list_categories.return_value = [("data_analysis", 2), ("speech_audio", 1)]
        result = await service.list_categories()
        assert result[0].display_name == "Data Analysis"
        assert result[1].display_name == "Speech Audio"


class TestTestTool:
    @pytest.fixture
    def tool_mock(self):
        tool = MagicMock()
        tool.id = uuid4()
        tool.langchain_class = "langchain_community.tools.tavily_search.TavilySearchResults"
        tool.required_keys = ["tavily_api_key"]
        return tool

    async def test_tool_not_found_raises(self, service, repo):
        repo.get_by_id.return_value = None
        request = ToolTestRequest(api_keys={"k": "v"}, input={"query": "test"})
        with pytest.raises(EntityNotFoundError):
            await service.test_tool(uuid4(), request)

    async def test_no_langchain_class_raises(self, service, repo):
        tool = MagicMock()
        tool.langchain_class = None
        repo.get_by_id.return_value = tool
        request = ToolTestRequest(api_keys={"k": "v"}, input={"query": "test"})
        with pytest.raises(ValidationError):
            await service.test_tool(uuid4(), request)

    async def test_missing_required_keys_raises(self, service, repo, tool_mock):
        repo.get_by_id.return_value = tool_mock
        request = ToolTestRequest(api_keys={}, input={"query": "test"})
        with pytest.raises(ValidationError, match="tavily_api_key"):
            await service.test_tool(tool_mock.id, request)

    @patch("app.services.tool._instantiate_tool")
    async def test_successful_execution(self, mock_instantiate, service, repo, tool_mock):
        repo.get_by_id.return_value = tool_mock
        mock_tool_instance = AsyncMock()
        mock_tool_instance.ainvoke.return_value = "search results here"
        mock_instantiate.return_value = mock_tool_instance

        request = ToolTestRequest(
            api_keys={"tavily_api_key": "test-key"},
            input={"query": "test"},
        )
        result = await service.test_tool(tool_mock.id, request)

        assert result.status == "success"
        assert result.output == "search results here"
        assert result.error is None
        assert result.latency_ms >= 0
        repo.update_test_result.assert_called_once()

    @patch("app.services.tool._instantiate_tool")
    async def test_failed_execution(self, mock_instantiate, service, repo, tool_mock):
        repo.get_by_id.return_value = tool_mock
        mock_tool_instance = AsyncMock()
        mock_tool_instance.ainvoke.side_effect = RuntimeError("API key invalid")
        mock_instantiate.return_value = mock_tool_instance

        request = ToolTestRequest(
            api_keys={"tavily_api_key": "bad-key"},
            input={"query": "test"},
        )
        result = await service.test_tool(tool_mock.id, request)

        assert result.status == "failed"
        assert result.output is None
        assert "RuntimeError" in result.error
        assert "API key invalid" in result.error
        repo.update_test_result.assert_called_once()
