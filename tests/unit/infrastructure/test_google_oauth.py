"""Tests for app.infrastructure.google_oauth — GoogleOAuthClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from app.core.exceptions import ServiceError, ValidationError
from app.infrastructure.google_oauth import GoogleOAuthClient


@pytest.fixture
def client():
    return GoogleOAuthClient(
        client_id="test-client-id",
        client_secret="test-client-secret",
        timeout=5.0,
    )


def _mock_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = {"content-type": "application/json"}
    return resp


class TestExchangeCode:
    async def test_success(self, client):
        mock_resp = _mock_response(200, {
            "access_token": "ya29.access",
            "refresh_token": "1//refresh",
            "expires_in": 3600,
            "scope": "openid email",
        })
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.exchange_code("auth-code", "")

        assert result.access_token == "ya29.access"
        assert result.refresh_token == "1//refresh"
        assert result.expires_in == 3600
        assert result.scope == "openid email"

    async def test_invalid_code_raises_validation_error(self, client):
        mock_resp = _mock_response(400, {
            "error": "invalid_grant",
            "error_description": "Code has expired",
        })
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(ValidationError, match="expired"):
                await client.exchange_code("bad-code", "")

    async def test_network_error_raises_service_error(self, client):
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.side_effect = httpx.ConnectError("Connection refused")
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(ServiceError, match="unavailable"):
                await client.exchange_code("code", "")


class TestRefreshAccessToken:
    async def test_success(self, client):
        mock_resp = _mock_response(200, {
            "access_token": "ya29.fresh",
            "expires_in": 3600,
            "scope": "openid",
        })
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.refresh_access_token("1//refresh")

        assert result.access_token == "ya29.fresh"
        assert result.refresh_token is None

    async def test_revoked_raises_service_error(self, client):
        mock_resp = _mock_response(400, {
            "error": "invalid_grant",
            "error_description": "Token has been revoked",
        })
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.post.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(ServiceError, match="revoked"):
                await client.refresh_access_token("1//bad_refresh")


class TestGetUserInfo:
    async def test_success(self, client):
        mock_resp = _mock_response(200, {
            "email": "jane@example.com",
            "name": "Jane Doe",
            "picture": "https://photo.url",
        })
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            result = await client.get_user_info("ya29.access")

        assert result.email == "jane@example.com"
        assert result.name == "Jane Doe"

    async def test_failure_raises_service_error(self, client):
        mock_resp = _mock_response(401, {"error": "invalid_token"})
        with patch("app.infrastructure.google_oauth.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get.return_value = mock_resp
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http

            with pytest.raises(ServiceError, match="user info"):
                await client.get_user_info("bad-token")
