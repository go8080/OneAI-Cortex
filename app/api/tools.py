"""Tool endpoints — register, list, and manage tools."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.repositories.tool import ToolRepository
from app.schemas.tool import ToolCreate, ToolResponse, ToolUpdate
from app.services.tool import ToolService

router = APIRouter()


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> ToolService:
    return ToolService(ToolRepository(db), request.app.state.encryption)


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    framework: str | None = Query(None),
    _user: AuthenticatedUser = Depends(get_current_user),
    service: ToolService = Depends(_get_service),
) -> list[ToolResponse]:
    """List all active tools, optionally filtered by framework."""
    tools = await service.list_tools(framework=framework)
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
