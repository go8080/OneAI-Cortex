"""Integration tests for health endpoints."""

from __future__ import annotations

import pytest


class TestLiveness:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data

    async def test_health_no_auth_required(self, client):
        """Health endpoint should work without auth header."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
