"""Integration tests for agent CRUD endpoints."""

from __future__ import annotations

import pytest


class TestAgentsCRUD:
    async def test_create_agent(self, client):
        resp = await client.post("/api/v1/agents", json={
            "name": "Test Agent",
            "description": "A test agent",
            "framework": "deepagents",
            "config": {"system_prompt": "Be helpful"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Agent"
        assert data["framework"] == "deepagents"
        assert data["status"] == "draft"
        assert data["current_version"] == 1

    async def test_list_agents_empty(self, client):
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_agents_paginated(self, client):
        # Create an agent first
        await client.post("/api/v1/agents", json={"name": "Agent 1"})

        resp = await client.get("/api/v1/agents?page=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["limit"] == 10
        assert data["total"] >= 1

    async def test_get_agent(self, client):
        create_resp = await client.post("/api/v1/agents", json={"name": "Get Me"})
        agent_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Me"

    async def test_update_agent(self, client):
        create_resp = await client.post("/api/v1/agents", json={"name": "Original"})
        agent_id = create_resp.json()["id"]

        resp = await client.put(f"/api/v1/agents/{agent_id}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    async def test_delete_agent(self, client):
        create_resp = await client.post("/api/v1/agents", json={"name": "Delete Me"})
        agent_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/agents/{agent_id}")
        assert resp.status_code == 204

        # Should be soft-deleted
        get_resp = await client.get(f"/api/v1/agents/{agent_id}")
        assert get_resp.status_code == 404

    async def test_get_nonexistent_agent_returns_404(self, client):
        resp = await client.get("/api/v1/agents/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    async def test_create_agent_empty_name_fails(self, client):
        resp = await client.post("/api/v1/agents", json={"name": ""})
        assert resp.status_code == 422


class TestAgentVersions:
    async def test_list_versions(self, client):
        create_resp = await client.post("/api/v1/agents", json={
            "name": "Versioned Agent",
            "config": {"model": "openai:gpt-4o"},
        })
        agent_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/agents/{agent_id}/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["version"] == 1

    async def test_get_specific_version(self, client):
        create_resp = await client.post("/api/v1/agents", json={"name": "V Agent"})
        agent_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/agents/{agent_id}/versions/1")
        assert resp.status_code == 200
        assert resp.json()["version"] == 1

    async def test_update_config_creates_new_version(self, client):
        create_resp = await client.post("/api/v1/agents", json={
            "name": "Multi Version",
            "config": {"model": "openai:gpt-4o"},
        })
        agent_id = create_resp.json()["id"]

        # Update with new config
        await client.put(f"/api/v1/agents/{agent_id}", json={
            "config": {"model": "anthropic:claude-sonnet-4-6"},
            "change_summary": "Switched to Claude",
        })

        # Should now have 2 versions
        resp = await client.get(f"/api/v1/agents/{agent_id}/versions")
        assert len(resp.json()) == 2
