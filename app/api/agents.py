"""Agent endpoints — create, list, update, delete, and version management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.repositories.agent import AgentRepository
from app.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    AgentVersionResponse,
    PaginatedResponse,
)
from app.services.agent import AgentService

router = APIRouter()


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> AgentService:
    return AgentService(
        AgentRepository(db),
        request.app.state.adapter_registry,
        request.app.state.encryption,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> AgentResponse:
    """Create a new agent with its initial configuration."""
    return await service.create_agent(
        user.user_id, body.name, body.description, body.framework, body.config
    )


@router.get("", response_model=PaginatedResponse)
async def list_agents(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> PaginatedResponse:
    """List all agents for the authenticated user."""
    agents, total = await service.list_agents(user.user_id, page=page, limit=limit)
    return PaginatedResponse(
        items=agents,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> AgentResponse:
    """Get an agent by ID."""
    return await service.get_agent(agent_id, user.user_id)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    body: AgentUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> AgentResponse:
    """Update an agent. Config changes create a new version."""
    return await service.update_agent(
        agent_id,
        user.user_id,
        name=body.name,
        description=body.description,
        status=body.status,
        config=body.config,
        change_summary=body.change_summary,
    )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> None:
    """Soft-delete an agent."""
    await service.delete_agent(agent_id, user.user_id)


@router.get("/{agent_id}/versions", response_model=list[AgentVersionResponse])
async def list_versions(
    agent_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> list[AgentVersionResponse]:
    """List all versions of an agent."""
    versions = await service.list_versions(agent_id, user.user_id, page=page, limit=limit)
    return [AgentVersionResponse.model_validate(v) for v in versions]


@router.get("/{agent_id}/versions/{version}", response_model=AgentVersionResponse)
async def get_version(
    agent_id: UUID,
    version: int,
    user: AuthenticatedUser = Depends(get_current_user),
    service: AgentService = Depends(_get_service),
) -> AgentVersionResponse:
    """Get a specific version of an agent."""
    ver = await service.get_version(agent_id, user.user_id, version)
    return AgentVersionResponse.model_validate(ver)
