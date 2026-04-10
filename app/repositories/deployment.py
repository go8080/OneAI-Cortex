"""Deployment repository — data access for agent deployments."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment

__all__ = ["DeploymentRepository"]


class DeploymentRepository:
    """Data access for deployments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> Deployment:
        instance = Deployment(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_id(self, deployment_id: UUID) -> Deployment | None:
        stmt = select(Deployment).where(Deployment.id == deployment_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_agent(self, agent_id: UUID) -> list[Deployment]:
        stmt = (
            select(Deployment)
            .where(Deployment.agent_id == agent_id)
            .order_by(Deployment.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, deployment_id: UUID, data: dict[str, Any]) -> Deployment | None:
        deployment = await self.get_by_id(deployment_id)
        if deployment is None:
            return None
        for key, value in data.items():
            setattr(deployment, key, value)
        await self._session.flush()
        return deployment
