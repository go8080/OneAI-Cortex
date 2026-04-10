"""Integration tests for framework endpoints."""

from __future__ import annotations

import pytest


class TestFrameworks:
    async def test_list_frameworks(self, client):
        resp = await client.get("/api/v1/frameworks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["framework_name"] == "deepagents"

    async def test_get_framework_by_name(self, client):
        resp = await client.get("/api/v1/frameworks/deepagents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["framework_name"] == "deepagents"
        assert "adapter_version" in data
        assert "sdk_compatibility" in data

    async def test_get_nonexistent_framework(self, client):
        resp = await client.get("/api/v1/frameworks/nonexistent")
        assert resp.status_code == 404
