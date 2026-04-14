"""Aggregates all v1 API routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.api_keys import router as api_keys_router
from app.api.connected_services import router as connected_services_router
from app.api.deployer import router as deployer_router
from app.api.evaluator import router as evaluator_router
from app.api.frameworks import router as frameworks_router
from app.api.health import router as health_router
from app.api.mcp_servers import router as mcp_servers_router
from app.api.runner import router as runner_router
from app.api.tools import router as tools_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(runner_router, prefix="/run", tags=["runner"])
api_router.include_router(evaluator_router, prefix="/agents", tags=["evaluator"])
api_router.include_router(deployer_router, prefix="/agents", tags=["deployer"])
api_router.include_router(frameworks_router, prefix="/frameworks", tags=["frameworks"])
api_router.include_router(tools_router, prefix="/tools", tags=["tools"])
api_router.include_router(mcp_servers_router, prefix="/mcp-servers", tags=["mcp-servers"])
api_router.include_router(connected_services_router, prefix="/connected-services", tags=["connected-services"])
