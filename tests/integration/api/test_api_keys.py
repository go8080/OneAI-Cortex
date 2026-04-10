"""Integration tests for API key endpoints."""

from __future__ import annotations

import pytest


class TestApiKeysCRUD:
    async def test_create_api_key(self, client):
        resp = await client.post("/api/v1/api-keys", json={"name": "test-key"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-key"
        assert "key" in data
        assert data["key"].startswith("ctx_")
        assert "key_prefix" in data
        assert "id" in data

    async def test_list_api_keys(self, client):
        # Create a key first
        await client.post("/api/v1/api-keys", json={"name": "list-key"})

        resp = await client.get("/api/v1/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Summary shouldn't include raw key
        assert "key" not in data[0]
        assert "key_prefix" in data[0]

    async def test_revoke_api_key(self, client):
        create_resp = await client.post("/api/v1/api-keys", json={"name": "revoke-me"})
        key_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/api-keys/{key_id}")
        assert resp.status_code == 204

    async def test_create_empty_name_fails(self, client):
        resp = await client.post("/api/v1/api-keys", json={"name": ""})
        assert resp.status_code == 422
