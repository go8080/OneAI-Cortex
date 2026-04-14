"""Integration tests for connected services endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.google_oauth import GoogleTokenResult, GoogleUserInfo


class TestConnectGoogle:
    async def test_connect_creates_connection(self, client, app):
        """POST /connected-services/google/connect with valid code creates connection."""
        mock_google = AsyncMock()
        mock_google.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.test",
            refresh_token="1//test_refresh",
            expires_in=3600,
            scope="openid https://www.googleapis.com/auth/gmail.modify",
        )
        mock_google.get_user_info.return_value = GoogleUserInfo(
            email="test@example.com", name="Test User", picture=None,
        )
        app.state.google_oauth_client = mock_google

        resp = await client.post("/api/v1/connected-services/google/connect", json={
            "code": "test-auth-code",
            "redirect_uri": "",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "google"
        assert data["provider_email"] == "test@example.com"
        assert data["status"] == "active"
        assert "openid" in data["granted_scopes"]

    async def test_connect_without_google_configured(self, client, app):
        """POST /connected-services/google/connect returns 502 when Google not configured."""
        app.state.google_oauth_client = None

        resp = await client.post("/api/v1/connected-services/google/connect", json={
            "code": "test-code",
            "redirect_uri": "",
        })

        assert resp.status_code == 502
        assert "not configured" in resp.json()["message"]


class TestListConnections:
    async def test_list_empty(self, client, app):
        """GET /connected-services returns empty when no connections."""
        app.state.google_oauth_client = None

        resp = await client.get("/api/v1/connected-services")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_after_connect(self, client, app):
        """GET /connected-services returns connection after connect."""
        mock_google = AsyncMock()
        mock_google.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.test", refresh_token="1//test",
            expires_in=3600, scope="openid",
        )
        mock_google.get_user_info.return_value = GoogleUserInfo(
            email="test@example.com", name="Test", picture=None,
        )
        app.state.google_oauth_client = mock_google

        await client.post("/api/v1/connected-services/google/connect", json={
            "code": "code", "redirect_uri": "",
        })

        resp = await client.get("/api/v1/connected-services")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["provider"] == "google"


class TestGoogleScopes:
    async def test_not_connected(self, client, app):
        """GET /connected-services/google/scopes returns connected=false."""
        app.state.google_oauth_client = None

        resp = await client.get("/api/v1/connected-services/google/scopes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is False
        assert data["scopes"] == []
        assert data["email"] is None

    async def test_connected(self, client, app):
        """GET /connected-services/google/scopes returns scopes after connect."""
        mock_google = AsyncMock()
        mock_google.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.test", refresh_token="1//test",
            expires_in=3600, scope="openid gmail.modify",
        )
        mock_google.get_user_info.return_value = GoogleUserInfo(
            email="test@example.com", name="Test", picture=None,
        )
        app.state.google_oauth_client = mock_google

        await client.post("/api/v1/connected-services/google/connect", json={
            "code": "code", "redirect_uri": "",
        })

        resp = await client.get("/api/v1/connected-services/google/scopes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert "openid" in data["scopes"]
        assert data["email"] == "test@example.com"


class TestGoogleToken:
    async def test_no_connection_returns_404(self, client, app):
        """GET /connected-services/google/token returns 404 when not connected."""
        mock_google = AsyncMock()
        app.state.google_oauth_client = mock_google

        resp = await client.get("/api/v1/connected-services/google/token")
        assert resp.status_code == 404

    async def test_returns_fresh_token(self, client, app):
        """GET /connected-services/google/token returns fresh access token."""
        mock_google = AsyncMock()
        mock_google.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.initial", refresh_token="1//refresh",
            expires_in=3600, scope="openid",
        )
        mock_google.get_user_info.return_value = GoogleUserInfo(
            email="test@example.com", name="Test", picture=None,
        )
        mock_google.refresh_access_token.return_value = GoogleTokenResult(
            access_token="ya29.fresh", refresh_token=None,
            expires_in=3600, scope="openid",
        )
        app.state.google_oauth_client = mock_google

        # Connect first
        await client.post("/api/v1/connected-services/google/connect", json={
            "code": "code", "redirect_uri": "",
        })

        # Get fresh token
        resp = await client.get("/api/v1/connected-services/google/token")
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "ya29.fresh"
        assert data["expires_in"] == 3600


class TestDisconnectGoogle:
    async def test_disconnect_removes_connection(self, client, app):
        """DELETE /connected-services/google removes the connection."""
        mock_google = AsyncMock()
        mock_google.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.test", refresh_token="1//test",
            expires_in=3600, scope="openid",
        )
        mock_google.get_user_info.return_value = GoogleUserInfo(
            email="test@example.com", name="Test", picture=None,
        )
        app.state.google_oauth_client = mock_google

        # Connect
        await client.post("/api/v1/connected-services/google/connect", json={
            "code": "code", "redirect_uri": "",
        })

        # Disconnect
        resp = await client.delete("/api/v1/connected-services/google")
        assert resp.status_code == 204

        # Verify disconnected
        resp = await client.get("/api/v1/connected-services/google/scopes")
        data = resp.json()
        assert data["connected"] is False

    async def test_disconnect_not_connected_returns_404(self, client, app):
        """DELETE /connected-services/google returns 404 when not connected."""
        app.state.google_oauth_client = None

        resp = await client.delete("/api/v1/connected-services/google")
        assert resp.status_code == 404
