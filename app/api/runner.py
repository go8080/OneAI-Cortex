"""Runner endpoints — session management and agent execution via SSE."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.infrastructure.sse import sse_event_generator
from app.repositories.agent import AgentRepository
from app.repositories.session import SessionRepository
from app.schemas.runner import (
    ChatRequest,
    ResumeRequest,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
)
from app.infrastructure.google_oauth import GoogleOAuthClient
from app.repositories.connected_service import ConnectedServiceRepository
from app.services.connected_service import ConnectedServiceService
from app.services.runner import RunnerService

router = APIRouter()


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> RunnerService:
    google_client: GoogleOAuthClient | None = getattr(
        request.app.state, "google_oauth_client", None
    )
    connected_svc = ConnectedServiceService(
        ConnectedServiceRepository(db),
        google_client,
        request.app.state.encryption,
    )
    return RunnerService(
        SessionRepository(db),
        AgentRepository(db),
        request.app.state.adapter_registry,
        request.app.state.encryption,
        connected_service=connected_svc,
    )


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    service: RunnerService = Depends(_get_service),
) -> SessionResponse:
    """Create a new chat session for an agent."""
    session = await service.create_session(body.agent_id, user.user_id, body.title)
    return SessionResponse.model_validate(session)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: AuthenticatedUser = Depends(get_current_user),
    service: RunnerService = Depends(_get_service),
) -> list[SessionResponse]:
    """List all sessions for the authenticated user."""
    sessions = await service.list_user_sessions(user.user_id)
    return [SessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: RunnerService = Depends(_get_service),
) -> SessionDetailResponse:
    """Get a single session with its messages."""
    session, messages = await service.get_session_with_messages(session_id, user.user_id)
    return SessionDetailResponse.model_validate({
        **SessionResponse.model_validate(session).model_dump(),
        "messages": messages,
    })


@router.post("/sessions/{session_id}/chat")
async def chat(
    session_id: UUID,
    body: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: RunnerService = Depends(_get_service),
) -> EventSourceResponse:
    """Send a message and stream agent response via SSE."""
    events = service.run_session(session_id, user.user_id, body.message)
    return EventSourceResponse(sse_event_generator(events))


@router.post("/sessions/{session_id}/resume")
async def resume_session(
    session_id: UUID,
    body: ResumeRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    service: RunnerService = Depends(_get_service),
) -> EventSourceResponse:
    """Resume execution after HITL interrupt."""
    events = service.resume_session(
        session_id, user.user_id, body.approved, body.modified_args
    )
    return EventSourceResponse(sse_event_generator(events))
