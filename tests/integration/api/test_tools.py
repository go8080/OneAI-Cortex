"""Integration tests for tool registry endpoints."""

from __future__ import annotations

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
