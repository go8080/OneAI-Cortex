"""Google OAuth 2.0 HTTP client — token exchange and user info."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from app.core.exceptions import ServiceError, ValidationError

__all__ = ["GoogleOAuthClient", "GoogleTokenResult", "GoogleUserInfo"]

logger = structlog.get_logger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@dataclass(frozen=True, slots=True)
class GoogleTokenResult:
    """Result of a Google OAuth token exchange or refresh."""

    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str


@dataclass(frozen=True, slots=True)
class GoogleUserInfo:
    """User profile data from Google's userinfo endpoint."""

    email: str
    name: str | None = None
    picture: str | None = None


class GoogleOAuthClient:
    """Async HTTP client for Google OAuth 2.0 endpoints."""

    def __init__(
        self, client_id: str, client_secret: str, timeout: float = 10.0
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout

    async def exchange_code(
        self, code: str, redirect_uri: str
    ) -> GoogleTokenResult:
        """Exchange an authorization code for tokens.

        Calls POST https://oauth2.googleapis.com/token with
        grant_type=authorization_code.
        """
        effective_redirect_uri = redirect_uri or "postmessage"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": effective_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
        except httpx.HTTPError as exc:
            logger.error("google_oauth.exchange_code_network_error", error=str(exc))
            raise ServiceError("Google OAuth service unavailable") from exc

        if resp.status_code != 200:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_desc = body.get("error_description", body.get("error", "unknown"))
            logger.warning(
                "google_oauth.exchange_code_failed",
                status=resp.status_code,
                error=error_desc,
            )
            raise ValidationError(
                f"Invalid or expired Google authorization code: {error_desc}"
            )

        data = resp.json()
        return GoogleTokenResult(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 3600),
            scope=data.get("scope", ""),
        )

    async def refresh_access_token(
        self, refresh_token: str
    ) -> GoogleTokenResult:
        """Get a fresh access token using a stored refresh token.

        Calls POST https://oauth2.googleapis.com/token with
        grant_type=refresh_token.

        Raises ServiceError with 'revoked' in message if Google returns
        invalid_grant (token revoked by user).
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "refresh_token": refresh_token,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "grant_type": "refresh_token",
                    },
                )
        except httpx.HTTPError as exc:
            logger.error("google_oauth.refresh_network_error", error=str(exc))
            raise ServiceError("Google OAuth service unavailable") from exc

        if resp.status_code != 200:
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_code = body.get("error", "")

            if error_code == "invalid_grant":
                logger.warning("google_oauth.token_revoked")
                raise ServiceError(
                    "Google access has been revoked. Please reconnect."
                )

            error_desc = body.get("error_description", error_code or "unknown")
            logger.warning(
                "google_oauth.refresh_failed",
                status=resp.status_code,
                error=error_desc,
            )
            raise ServiceError(
                f"Google token refresh failed: {error_desc}"
            )

        data = resp.json()
        return GoogleTokenResult(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 3600),
            scope=data.get("scope", ""),
        )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Fetch user profile from Google's userinfo endpoint."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            logger.error("google_oauth.userinfo_network_error", error=str(exc))
            raise ServiceError("Google OAuth service unavailable") from exc

        if resp.status_code != 200:
            logger.warning(
                "google_oauth.userinfo_failed", status=resp.status_code
            )
            raise ServiceError("Failed to fetch Google user info")

        data = resp.json()
        return GoogleUserInfo(
            email=data.get("email", ""),
            name=data.get("name"),
            picture=data.get("picture"),
        )
