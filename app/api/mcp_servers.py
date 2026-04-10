"""MCP server endpoints — register, list, test, and manage MCP servers."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.infrastructure.mcp_client import MCPClient
from app.repositories.mcp_server import McpServerRepository
from app.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerResponse,
    MCPTestResultResponse,
)
from app.services.mcp_server import McpServerService

router = APIRouter()


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> McpServerService:
    return McpServerService(
        McpServerRepository(db), request.app.state.encryption, MCPClient()
    )


@router.post("", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    body: MCPServerCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    service: McpServerService = Depends(_get_service),
) -> MCPServerResponse:
    """Register a new MCP server."""
    server = await service.create_server(user.user_id, body)
    return MCPServerResponse.model_validate(server)


@router.get("", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    user: AuthenticatedUser = Depends(get_current_user),
    service: McpServerService = Depends(_get_service),
) -> list[MCPServerResponse]:
    """List all MCP servers for the authenticated user."""
    servers = await service.list_servers(user.user_id)
    return [MCPServerResponse.model_validate(s) for s in servers]


@router.get("/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: McpServerService = Depends(_get_service),
) -> MCPServerResponse:
    """Get an MCP server by ID."""
    server = await service.get_server(server_id, user.user_id)
    return MCPServerResponse.model_validate(server)


@router.post("/{server_id}/test", response_model=MCPTestResultResponse)
async def test_mcp_server(
    server_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: McpServerService = Depends(_get_service),
) -> MCPTestResultResponse:
    """Test connectivity to an MCP server and discover its tools."""
    result = await service.test_server(server_id, user.user_id)
    return MCPTestResultResponse(
        reachable=result.reachable,
        tools_discovered=[
            {"name": t.name, "description": t.description} for t in result.tools_discovered
        ],
        error=result.error,
        latency_ms=result.latency_ms,
    )


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    service: McpServerService = Depends(_get_service),
) -> None:
    """Delete an MCP server."""
    await service.delete_server(server_id, user.user_id)
