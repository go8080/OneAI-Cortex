"""Agent repository — data access for agents and agent versions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentVersion

__all__ = ["AgentRepository"]


class AgentRepository:
    """Data access for agents and their versions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # === Agents ===

    async def create(self, data: dict[str, Any]) -> Agent:
        """Create a new agent."""
        instance = Agent(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_by_id(self, agent_id: UUID, *, include_deleted: bool = False) -> Agent | None:
        """Get an agent by ID."""
        stmt = select(Agent).where(Agent.id == agent_id)
        if not include_deleted:
            stmt = stmt.where(Agent.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Agent]:
        """List agents for a user (excluding soft-deleted)."""
        stmt = (
            select(Agent)
            .where(Agent.user_id == user_id, Agent.is_deleted.is_(False))
            .order_by(Agent.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        """Count agents for a user (excluding soft-deleted)."""
        stmt = (
            select(func.count())
            .select_from(Agent)
            .where(Agent.user_id == user_id, Agent.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update(self, agent_id: UUID, data: dict[str, Any]) -> Agent | None:
        """Update an agent. Returns None if not found."""
        agent = await self.get_by_id(agent_id)
        if agent is None:
            return None
        for key, value in data.items():
            setattr(agent, key, value)
        await self._session.flush()
        return agent

    async def soft_delete(self, agent_id: UUID) -> bool:
        """Soft-delete an agent. Returns True if found."""
        agent = await self.get_by_id(agent_id)
        if agent is None:
            return False
        agent.is_deleted = True
        await self._session.flush()
        return True

    # === Versions ===

    async def create_version(self, data: dict[str, Any]) -> AgentVersion:
        """Create a new agent version."""
        instance = AgentVersion(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_version(self, agent_id: UUID, version: int) -> AgentVersion | None:
        """Get a specific version of an agent."""
        stmt = select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version == version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        agent_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AgentVersion]:
        """List versions for an agent, newest first."""
        stmt = (
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_version(self, agent_id: UUID) -> AgentVersion | None:
        """Get the latest version for an agent."""
        stmt = (
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
