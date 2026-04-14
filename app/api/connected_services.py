"""Connected services endpoints — OAuth connections to external providers."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.infrastructure.google_oauth import GoogleOAuthClient
from app.repositories.connected_service import ConnectedServiceRepository
from app.schemas.connected_service import (
    ConnectedServiceListResponse,
    ConnectedServiceResponse,
    GoogleConnectRequest,
    GoogleScopesResponse,
    GoogleTokenResponse,
)
from app.services.connected_service import ConnectedServiceService

router = APIRouter()


def _get_service(
    request: Request, db: AsyncSession = Depends(get_db)
) -> ConnectedServiceService:
    google_client: GoogleOAuthClient | None = getattr(
        request.app.state, "google_oauth_client", None
    )
    return ConnectedServiceService(
        ConnectedServiceRepository(db),
        google_client,
        request.app.state.encryption,
    )


@router.post(
    "/google/connect",
    response_model=ConnectedServiceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": ConnectedServiceResponse}},
)
async def connect_google(
    body: GoogleConnectRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectedServiceService = Depends(_get_service),
) -> ConnectedServiceResponse:
    """Exchange a Google authorization code for tokens and store the connection."""
    result = await service.connect_google(user.user_id, body.code, body.redirect_uri)
    # FastAPI doesn't natively support dynamic status codes in the same
    # response_model, so we always return 201. The _is_new flag is internal.
    result.pop("_is_new", None)
    return ConnectedServiceResponse(**result)


@router.get("", response_model=ConnectedServiceListResponse)
async def list_connections(
    user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectedServiceService = Depends(_get_service),
) -> ConnectedServiceListResponse:
    """List all connected services for the authenticated user."""
    items = await service.list_connections(user.user_id)
    cleaned = []
    for item in items:
        item.pop("_is_new", None)
        cleaned.append(ConnectedServiceResponse(**item))
    return ConnectedServiceListResponse(items=cleaned, total=len(cleaned))


@router.get("/google/scopes", response_model=GoogleScopesResponse)
async def get_google_scopes(
    user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectedServiceService = Depends(_get_service),
) -> GoogleScopesResponse:
    """Get Google connection status and granted scopes."""
    result = await service.get_google_scopes(user.user_id)
    return GoogleScopesResponse(**result)


@router.get("/google/token", response_model=GoogleTokenResponse)
async def get_google_token(
    user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectedServiceService = Depends(_get_service),
) -> GoogleTokenResponse:
    """Get a fresh Google access token from the stored refresh token."""
    result = await service.get_google_token(user.user_id)
    return GoogleTokenResponse(**result)


@router.delete("/google", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google(
    user: AuthenticatedUser = Depends(get_current_user),
    service: ConnectedServiceService = Depends(_get_service),
) -> None:
    """Disconnect Google — permanently removes stored tokens."""
    await service.disconnect_google(user.user_id)
