"""Deployer service — business logic for agent deployment and SDK generation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import EntityNotFoundError, ValidationError
from app.repositories.agent import AgentRepository
from app.repositories.deployment import DeploymentRepository

__all__ = ["DeployerService"]


class DeployerService:
    """Orchestrates agent deployment operations."""

    def __init__(
        self,
        repo: DeploymentRepository,
        agent_repo: AgentRepository,
    ) -> None:
        self._repo = repo
        self._agents = agent_repo

    async def deploy_agent(
        self, agent_id: UUID, user_id: UUID, deploy_type: str,
        agent_version: int | None = None,
    ) -> object:
        """Deploy an agent as hosted or SDK download."""
        agent = await self._agents.get_by_id(agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", agent_id)

        if deploy_type not in ("hosted", "sdk_download"):
            raise ValidationError(f"Invalid deployment type: {deploy_type}")

        version = agent_version or agent.current_version
        endpoint_url = f"/api/v1/hosted/{agent_id}" if deploy_type == "hosted" else None

        return await self._repo.create({
            "agent_id": agent_id,
            "user_id": user_id,
            "agent_version": version,
            "type": deploy_type,
            "endpoint_url": endpoint_url,
        })

    async def undeploy(self, deployment_id: UUID, user_id: UUID) -> None:
        """Stop a deployment."""
        deployment = await self._repo.get_by_id(deployment_id)
        if deployment is None or deployment.user_id != user_id:
            raise EntityNotFoundError("Deployment", "id", deployment_id)

        await self._repo.update(deployment_id, {
            "status": "stopped",
            "stopped_at": datetime.now(UTC),
        })

    async def list_deployments(self, agent_id: UUID) -> list:
        return await self._repo.list_by_agent(agent_id)
