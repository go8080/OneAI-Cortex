"""Session repository — data access for chat sessions and messages."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as DbSession

from app.models.session import Message, Session

__all__ = ["SessionRepository"]


class SessionRepository:
    """Data access for sessions and messages."""

    def __init__(self, session: DbSession) -> None:
        self._session = session

    async def create_session(self, data: dict[str, Any]) -> Session:
        """Create a new chat session."""
        instance = Session(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_session(self, session_id: UUID) -> Session | None:
        """Get a session by ID."""
        stmt = select(Session).where(Session.id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(
        self, agent_id: UUID, user_id: UUID, *, active_only: bool = True
    ) -> list[Session]:
        """List sessions for an agent + user."""
        stmt = select(Session).where(
            Session.agent_id == agent_id, Session.user_id == user_id
        )
        if active_only:
            stmt = stmt.where(Session.is_active.is_(True))
        stmt = stmt.order_by(Session.updated_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add_message(self, data: dict[str, Any]) -> Message:
        """Add a message to a session."""
        instance = Message(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_messages(self, session_id: UUID) -> list[Message]:
        """Get all messages for a session in chronological order."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
