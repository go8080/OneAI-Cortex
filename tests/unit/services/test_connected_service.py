"""Tests for app.services.connected_service — ConnectedServiceService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.core.encryption import SecretEncryption
from app.core.exceptions import EntityNotFoundError, ServiceError, ValidationError
from app.infrastructure.google_oauth import GoogleTokenResult, GoogleUserInfo
from app.services.connected_service import ConnectedServiceService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def google_client():
    return AsyncMock()


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


@pytest.fixture
def service(repo, google_client, encryption):
    return ConnectedServiceService(repo, google_client, encryption)


USER_ID = uuid4()


class TestConnectGoogle:
    async def test_creates_new_connection(self, service, repo, google_client):
        google_client.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.access",
            refresh_token="1//refresh",
            expires_in=3600,
            scope="openid https://www.googleapis.com/auth/gmail.modify",
        )
        google_client.get_user_info.return_value = GoogleUserInfo(
            email="jane@example.com", name="Jane", picture=None,
        )
        repo.get_by_user_and_provider.return_value = None
        repo.create.return_value = MagicMock(
            id=uuid4(), provider="google", provider_email="jane@example.com",
            status="active",
            granted_scopes="openid https://www.googleapis.com/auth/gmail.modify",
            created_at=MagicMock(), updated_at=MagicMock(),
        )

        result = await service.connect_google(USER_ID, "auth-code", "")

        google_client.exchange_code.assert_called_once_with("auth-code", "")
        google_client.get_user_info.assert_called_once_with("ya29.access")
        repo.create.assert_called_once()

        create_data = repo.create.call_args[0][0]
        assert create_data["provider"] == "google"
        assert create_data["provider_email"] == "jane@example.com"
        assert create_data["status"] == "active"
        # Refresh token should be encrypted (not plaintext)
        assert create_data["refresh_token"] != "1//refresh"
        assert create_data["refresh_token"].startswith("gAAAAA")
        assert result["_is_new"] is True

    async def test_reconnect_updates_existing(self, service, repo, google_client):
        existing = MagicMock(id=uuid4())
        repo.get_by_user_and_provider.return_value = existing
        google_client.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.new", refresh_token="1//new_refresh",
            expires_in=3600, scope="openid calendar",
        )
        google_client.get_user_info.return_value = GoogleUserInfo(
            email="jane@example.com", name="Jane", picture=None,
        )
        repo.update.return_value = MagicMock(
            id=existing.id, provider="google", provider_email="jane@example.com",
            status="active", granted_scopes="openid calendar",
            created_at=MagicMock(), updated_at=MagicMock(),
        )

        result = await service.connect_google(USER_ID, "new-code", "")

        repo.create.assert_not_called()
        repo.update.assert_called_once()
        assert result["_is_new"] is False

    async def test_no_refresh_token_raises(self, service, google_client):
        google_client.exchange_code.return_value = GoogleTokenResult(
            access_token="ya29.access", refresh_token=None,
            expires_in=3600, scope="openid",
        )
        with pytest.raises(ValidationError, match="refresh token"):
            await service.connect_google(USER_ID, "code", "")

    async def test_google_not_configured_raises(self, repo, encryption):
        svc = ConnectedServiceService(repo, None, encryption)
        with pytest.raises(ServiceError, match="not configured"):
            await svc.connect_google(USER_ID, "code", "")


class TestGetGoogleScopes:
    async def test_connected(self, service, repo):
        repo.get_by_user_and_provider.return_value = MagicMock(
            granted_scopes="openid gmail.modify calendar",
            provider_email="jane@example.com",
        )
        result = await service.get_google_scopes(USER_ID)
        assert result["connected"] is True
        assert result["scopes"] == ["openid", "gmail.modify", "calendar"]
        assert result["email"] == "jane@example.com"

    async def test_not_connected(self, service, repo):
        repo.get_by_user_and_provider.return_value = None
        result = await service.get_google_scopes(USER_ID)
        assert result["connected"] is False
        assert result["scopes"] == []
        assert result["email"] is None


class TestGetGoogleToken:
    async def test_returns_fresh_token(self, service, repo, google_client, encryption):
        encrypted = encryption.encrypt("1//real_refresh")
        repo.get_by_user_and_provider.return_value = MagicMock(
            id=uuid4(), refresh_token=encrypted,
            granted_scopes="openid gmail.modify",
        )
        google_client.refresh_access_token.return_value = GoogleTokenResult(
            access_token="ya29.fresh", refresh_token=None,
            expires_in=3600, scope="openid gmail.modify",
        )

        result = await service.get_google_token(USER_ID)

        assert result["access_token"] == "ya29.fresh"
        assert result["expires_in"] == 3600
        assert "openid" in result["scopes"]

    async def test_no_connection_raises(self, service, repo):
        repo.get_by_user_and_provider.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.get_google_token(USER_ID)

    async def test_revoked_token_updates_status(self, service, repo, google_client, encryption):
        encrypted = encryption.encrypt("1//revoked_refresh")
        conn = MagicMock(id=uuid4(), refresh_token=encrypted)
        repo.get_by_user_and_provider.return_value = conn
        google_client.refresh_access_token.side_effect = ServiceError(
            "Google access has been revoked. Please reconnect."
        )

        with pytest.raises(ServiceError, match="revoked"):
            await service.get_google_token(USER_ID)

        repo.update.assert_called_once()
        update_data = repo.update.call_args[0][1]
        assert update_data["status"] == "revoked"

    async def test_google_not_configured_raises(self, repo, encryption):
        svc = ConnectedServiceService(repo, None, encryption)
        with pytest.raises(ServiceError, match="not configured"):
            await svc.get_google_token(USER_ID)


class TestDisconnectGoogle:
    async def test_deletes_connection(self, service, repo):
        conn = MagicMock(id=uuid4())
        repo.get_by_user_and_provider.return_value = conn
        repo.delete.return_value = True

        await service.disconnect_google(USER_ID)
        repo.delete.assert_called_once_with(conn.id)

    async def test_no_connection_raises(self, service, repo):
        repo.get_by_user_and_provider.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.disconnect_google(USER_ID)


class TestListConnections:
    async def test_returns_all(self, service, repo):
        repo.list_by_user.return_value = [
            MagicMock(
                id=uuid4(), provider="google", provider_email="j@example.com",
                status="active", granted_scopes="openid",
                created_at=MagicMock(), updated_at=MagicMock(),
            ),
        ]
        result = await service.list_connections(USER_ID)
        assert len(result) == 1
        assert result[0]["provider"] == "google"

    async def test_returns_empty(self, service, repo):
        repo.list_by_user.return_value = []
        result = await service.list_connections(USER_ID)
        assert result == []
