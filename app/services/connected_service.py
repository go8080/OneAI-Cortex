"""Connected service — business logic for OAuth provider connections."""

from __future__ import annotations

from uuid import UUID

import structlog

from app.core.constants import ConnectionStatus, ServiceProvider
from app.core.encryption import SecretEncryption
from app.core.exceptions import EntityNotFoundError, ServiceError, ValidationError
from app.infrastructure.google_oauth import GoogleOAuthClient
from app.repositories.connected_service import ConnectedServiceRepository

__all__ = ["ConnectedServiceService"]

logger = structlog.get_logger(__name__)


class ConnectedServiceService:
    """Orchestrates connected service operations — OAuth, token storage, refresh."""

    def __init__(
        self,
        repo: ConnectedServiceRepository,
        google_client: GoogleOAuthClient | None,
        encryption: SecretEncryption,
    ) -> None:
        self._repo = repo
        self._google = google_client
        self._encryption = encryption

    async def connect_google(
        self, user_id: UUID, code: str, redirect_uri: str
    ) -> dict:
        """Exchange a Google authorization code for tokens and store the connection.

        Returns a dict suitable for ConnectedServiceResponse serialization.
        """
        if self._google is None:
            raise ServiceError("Google OAuth is not configured on this server")

        # Step 1: Exchange code for tokens
        token_result = await self._google.exchange_code(code, redirect_uri)

        if token_result.refresh_token is None:
            raise ValidationError(
                "Google did not return a refresh token. "
                "Ensure prompt=consent is set in the OAuth request."
            )

        # Step 2: Fetch user info
        user_info = await self._google.get_user_info(token_result.access_token)

        # Step 3: Encrypt refresh token
        encrypted_token = self._encryption.encrypt(token_result.refresh_token)

        # Step 4: Upsert connection
        existing = await self._repo.get_by_user_and_provider(
            user_id, ServiceProvider.GOOGLE
        )

        if existing is not None:
            updated = await self._repo.update(existing.id, {
                "refresh_token": encrypted_token,
                "granted_scopes": token_result.scope,
                "provider_email": user_info.email,
                "status": ConnectionStatus.ACTIVE,
            })
            logger.info(
                "connected_service.google_reconnected",
                user_id=str(user_id),
                email=user_info.email,
            )
            return self._to_response(updated, is_new=False)

        created = await self._repo.create({
            "user_id": user_id,
            "provider": ServiceProvider.GOOGLE,
            "provider_email": user_info.email,
            "refresh_token": encrypted_token,
            "granted_scopes": token_result.scope,
            "status": ConnectionStatus.ACTIVE,
        })
        logger.info(
            "connected_service.google_connected",
            user_id=str(user_id),
            email=user_info.email,
        )
        return self._to_response(created, is_new=True)

    async def get_google_scopes(self, user_id: UUID) -> dict:
        """Get Google connection status and granted scopes."""
        conn = await self._repo.get_by_user_and_provider(
            user_id, ServiceProvider.GOOGLE
        )
        if conn is None:
            return {"connected": False, "scopes": [], "email": None}

        return {
            "connected": True,
            "scopes": conn.granted_scopes.split() if conn.granted_scopes else [],
            "email": conn.provider_email,
        }

    async def get_google_token(self, user_id: UUID) -> dict:
        """Get a fresh Google access token from the stored refresh token.

        Returns dict with access_token, expires_in, scopes.
        """
        if self._google is None:
            raise ServiceError("Google OAuth is not configured on this server")

        conn = await self._repo.get_by_user_and_provider(
            user_id, ServiceProvider.GOOGLE
        )
        if conn is None:
            raise EntityNotFoundError(
                "ConnectedService", "provider", "google"
            )

        # Decrypt stored refresh token
        plaintext_refresh = self._encryption.decrypt(conn.refresh_token)

        # Refresh access token at Google
        try:
            token_result = await self._google.refresh_access_token(
                plaintext_refresh
            )
        except ServiceError as exc:
            if "revoked" in str(exc).lower():
                # Mark connection as revoked
                await self._repo.update(
                    conn.id, {"status": ConnectionStatus.REVOKED}
                )
                logger.warning(
                    "connected_service.google_token_revoked",
                    user_id=str(user_id),
                )
            raise

        logger.debug(
            "connected_service.google_token_issued",
            user_id=str(user_id),
            expires_in=token_result.expires_in,
        )
        return {
            "access_token": token_result.access_token,
            "expires_in": token_result.expires_in,
            "scopes": token_result.scope.split() if token_result.scope else [],
        }

    async def list_connections(self, user_id: UUID) -> list[dict]:
        """List all connected services for a user."""
        connections = await self._repo.list_by_user(user_id)
        return [self._to_response(c) for c in connections]

    async def disconnect_google(self, user_id: UUID) -> None:
        """Remove Google connection and stored tokens (hard delete)."""
        conn = await self._repo.get_by_user_and_provider(
            user_id, ServiceProvider.GOOGLE
        )
        if conn is None:
            raise EntityNotFoundError(
                "ConnectedService", "provider", "google"
            )

        await self._repo.delete(conn.id)
        logger.info(
            "connected_service.google_disconnected",
            user_id=str(user_id),
        )

    @staticmethod
    def _to_response(conn, is_new: bool = False) -> dict:
        """Convert a ConnectedService model to a response dict."""
        return {
            "id": conn.id,
            "provider": conn.provider,
            "provider_email": conn.provider_email,
            "status": conn.status,
            "granted_scopes": conn.granted_scopes.split() if conn.granted_scopes else [],
            "created_at": conn.created_at,
            "updated_at": conn.updated_at,
            "_is_new": is_new,
        }
