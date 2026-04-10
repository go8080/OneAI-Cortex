"""Deployer endpoints — deploy, undeploy, list deployments, download SDK."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.repositories.agent import AgentRepository
from app.repositories.deployment import DeploymentRepository
from app.schemas.deployer import DeploymentResponse, DeployRequest
from app.services.deployer import DeployerService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> DeployerService:
    return DeployerService(DeploymentRepository(db), AgentRepository(db))


@router.post(
    "/{agent_id}/deploy", response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def deploy_agent(
    agent_id: UUID,
    body: DeployRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: DeployerService = Depends(_get_service),
) -> DeploymentResponse:
    """Deploy an agent as hosted or SDK download."""
    deployment = await service.deploy_agent(
        agent_id, user.user_id, body.type, body.agent_version
    )
    return DeploymentResponse.model_validate(deployment)


@router.get("/{agent_id}/deployments", response_model=list[DeploymentResponse])
async def list_deployments(
    agent_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: DeployerService = Depends(_get_service),
) -> list[DeploymentResponse]:
    """List all deployments for an agent."""
    deployments = await service.list_deployments(agent_id)
    return [DeploymentResponse.model_validate(d) for d in deployments]


@router.delete("/deployments/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def undeploy(
    deployment_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: DeployerService = Depends(_get_service),
) -> None:
    """Stop a deployment."""
    await service.undeploy(deployment_id, user.user_id)
