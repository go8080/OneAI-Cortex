"""Tool endpoints — register, list, manage, browse categories, and playground."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.infrastructure.google_oauth import GoogleOAuthClient
from app.repositories.connected_service import ConnectedServiceRepository
from app.repositories.tool import ToolRepository
from app.schemas.tool import (
    ToolCategoryResponse,
    ToolCreate,
    ToolResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)
from app.services.connected_service import ConnectedServiceService
from app.services.tool import ToolService

router = APIRouter()


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> ToolService:
    return ToolService(ToolRepository(db), request.app.state.encryption)


def _get_connected_service(
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


@router.get("/categories", response_model=list[ToolCategoryResponse])
async def list_categories(
    _user: AuthenticatedUser = Depends(get_current_user),
    service: ToolService = Depends(_get_service),
) -> list[ToolCategoryResponse]:
    """List all tool categories with their tool counts."""
    return await service.list_categories()


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    framework: str | None = Query(None),
    category: str | None = Query(None),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: ToolService = Depends(_get_service),
) -> list[ToolResponse]:
    """List all active tools, optionally filtered by framework and/or category."""
    tools = await service.list_tools(framework=framework, category=category)
    return [ToolResponse.model_validate(t) for t in tools]


@router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    body: ToolCreate,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: ToolService = Depends(_get_service),
) -> ToolResponse:
    """Register a new custom tool."""
    tool = await service.create_tool(body)
    return ToolResponse.model_validate(tool)


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: ToolService = Depends(_get_service),
) -> ToolResponse:
    """Get a tool by ID."""
    tool = await service.get_tool(tool_id)
    return ToolResponse.model_validate(tool)


@router.post(
    "/{tool_id}/test",
    response_model=ToolTestResponse,
)
async def test_tool(
    tool_id: UUID,
    body: ToolTestRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: ToolService = Depends(_get_service),
    connected_svc: ConnectedServiceService = Depends(_get_connected_service),
) -> ToolTestResponse:
    """Tool playground — execute a tool with user-provided API keys and input.

    Returns the actual tool output on success, or the error message on failure.
    Always returns HTTP 200 — the ``status`` field indicates tool-level success/failure.
    For Google OAuth tools, the user's Connected Services token is used automatically.
    """
    # Try to fetch Google token for google_oauth tools
    google_token: str | None = None
    try:
        result = await connected_svc.get_google_token(user.user_id)
        google_token = result["access_token"]
    except Exception:
        pass  # Not connected or not configured — service.test_tool will handle

    return await service.test_tool(
        tool_id, body, google_access_token=google_token
    )
