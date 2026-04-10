"""HTTP client for OneAI-Auth service — profile enrichment only.

Authentication itself is local (JWT decode). This client is used when
Cortex needs user profile data (display name, avatar) from the auth service.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
import structlog

from app.config import get_settings

__all__ = ["AuthClient", "UserProfile"]

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class UserProfile:
    """User profile data from OneAI-Auth."""

    user_id: UUID
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


class AuthClient:
    """Async HTTP client for OneAI-Auth API."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0) -> None:
        self._base_url = base_url or get_settings().auth_service_url
        self._timeout = timeout

    async def get_user_profile(self, user_id: UUID, token: str) -> UserProfile | None:
        """Fetch user profile from OneAI-Auth. Returns None if unavailable."""
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                resp = await client.get(
                    f"/api/v1/users/{user_id}/profile",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "auth_client.profile_fetch_failed",
                        user_id=str(user_id),
                        status=resp.status_code,
                    )
                    return None
                data = resp.json()
                return UserProfile(
                    user_id=user_id,
                    email=data.get("email", ""),
                    display_name=data.get("display_name"),
                    avatar_url=data.get("avatar_url"),
                )
        except httpx.HTTPError as exc:
            logger.warning("auth_client.connection_error", error=str(exc))
            return None

    async def health_check(self) -> bool:
        """Check if OneAI-Auth service is reachable."""
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                resp = await client.get("/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
