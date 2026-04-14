"""Integration tests for tool registry endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


class TestToolsCRUD:
    async def test_create_tool(self, client):
        resp = await client.post("/api/v1/tools", json={
            "name": "web_search",
            "description": "Search the web",
            "framework": "deepagents",
            "tool_type": "custom",
            "schema": {"type": "function", "function": {"name": "web_search"}},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "web_search"
        assert data["framework"] == "deepagents"
        assert data["is_active"] is True

    async def test_list_tools(self, client):
        await client.post("/api/v1/tools", json={
            "name": "tool_list_test",
            "description": "test",
            "framework": "deepagents",
            "schema": {"type": "function"},
        })

        resp = await client.get("/api/v1/tools")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    async def test_get_tool(self, client):
        create_resp = await client.post("/api/v1/tools", json={
            "name": "get_tool_test",
            "description": "test",
            "framework": "deepagents",
            "schema": {"type": "function"},
        })
        tool_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/tools/{tool_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "get_tool_test"

    async def test_filter_by_framework(self, client):
        resp = await client.get("/api/v1/tools?framework=nonexistent")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_duplicate_name_fails(self, client):
        await client.post("/api/v1/tools", json={
            "name": "unique_tool",
            "description": "first",
            "framework": "deepagents",
            "schema": {},
        })
        resp = await client.post("/api/v1/tools", json={
            "name": "unique_tool",
            "description": "second",
            "framework": "deepagents",
            "schema": {},
        })
        assert resp.status_code == 409


class TestToolCategories:
    async def test_list_categories_empty(self, client):
        """No tools with categories → empty list."""
        resp = await client.get("/api/v1/tools/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_categories_with_tools(self, client):
        """Create tools with categories, verify category listing."""
        await client.post("/api/v1/tools", json={
            "name": "search_tool_1",
            "description": "Search tool",
            "framework": "langchain",
            "category": "search",
            "schema": {},
        })
        await client.post("/api/v1/tools", json={
            "name": "search_tool_2",
            "description": "Another search",
            "framework": "langchain",
            "category": "search",
            "schema": {},
        })
        await client.post("/api/v1/tools", json={
            "name": "browser_tool_1",
            "description": "Browser tool",
            "framework": "langchain",
            "category": "browser",
            "schema": {},
        })

        resp = await client.get("/api/v1/tools/categories")
        assert resp.status_code == 200
        categories = resp.json()
        assert len(categories) == 2

        names = {c["name"] for c in categories}
        assert names == {"browser", "search"}

        search_cat = next(c for c in categories if c["name"] == "search")
        assert search_cat["tool_count"] == 2
        assert search_cat["display_name"] == "Search"

    async def test_filter_tools_by_category(self, client):
        """Filter tools by category query parameter."""
        await client.post("/api/v1/tools", json={
            "name": "cat_filter_search",
            "description": "Search",
            "framework": "langchain",
            "category": "search",
            "schema": {},
        })
        await client.post("/api/v1/tools", json={
            "name": "cat_filter_browser",
            "description": "Browser",
            "framework": "langchain",
            "category": "browser",
            "schema": {},
        })

        resp = await client.get("/api/v1/tools?category=search")
        assert resp.status_code == 200
        tools = resp.json()
        assert len(tools) == 1
        assert tools[0]["category"] == "search"


class TestToolPlayground:
    async def _create_builtin_tool(self, client) -> str:
        """Helper — create a tool with langchain_class for playground testing."""
        resp = await client.post("/api/v1/tools", json={
            "name": "playground_test_tool",
            "description": "Test tool for playground",
            "framework": "langchain",
            "category": "search",
            "schema": {},
        })
        return resp.json()["id"]

    async def test_test_nonexistent_tool(self, client):
        """Testing a non-existent tool returns 404."""
        resp = await client.post(
            "/api/v1/tools/00000000-0000-0000-0000-000000000000/test",
            json={"api_keys": {"key": "val"}, "input": {"query": "test"}},
        )
        assert resp.status_code == 404

    async def test_test_tool_without_langchain_class(self, client):
        """Testing a custom tool (no langchain_class) returns 422 validation error."""
        create_resp = await client.post("/api/v1/tools", json={
            "name": "custom_no_class",
            "description": "Custom tool",
            "framework": "deepagents",
            "schema": {},
        })
        tool_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/tools/{tool_id}/test",
            json={"api_keys": {}, "input": {"query": "test"}},
        )
        assert resp.status_code == 422
