"""Integration tests for MCP server endpoints."""

from __future__ import annotations

import pytest


class TestMcpServersCRUD:
    async def test_create_stdio_server(self, client):
        resp = await client.post("/api/v1/mcp-servers", json={
            "name": "FS Tools",
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "FS Tools"
        assert data["transport"] == "stdio"
        assert data["status"] == "untested"

    async def test_create_sse_server(self, client):
        resp = await client.post("/api/v1/mcp-servers", json={
            "name": "Remote Tools",
            "transport": "sse",
            "url": "http://localhost:3001/sse",
        })
        assert resp.status_code == 201

    async def test_list_servers(self, client):
        await client.post("/api/v1/mcp-servers", json={
            "name": "List Test",
            "transport": "stdio",
            "command": "echo",
        })
        resp = await client.get("/api/v1/mcp-servers")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_server(self, client):
        create_resp = await client.post("/api/v1/mcp-servers", json={
            "name": "Get Test",
            "transport": "http",
            "url": "http://localhost:3002",
        })
        server_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/mcp-servers/{server_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Get Test"

    async def test_delete_server(self, client):
        create_resp = await client.post("/api/v1/mcp-servers", json={
            "name": "Delete Test",
            "transport": "stdio",
            "command": "echo",
        })
        server_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/mcp-servers/{server_id}")
        assert resp.status_code == 204

    async def test_invalid_transport_fails(self, client):
        resp = await client.post("/api/v1/mcp-servers", json={
            "name": "Bad Transport",
            "transport": "websocket",
        })
        assert resp.status_code == 422
