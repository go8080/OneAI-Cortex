"""FastAPI application factory — NOTHING else belongs here."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.core.encryption import SecretEncryption
from app.adapters.deepagents.adapter import DeepAgentsAdapter
from app.adapters.registry import AdapterRegistry
from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.infrastructure.auth_client import AuthClient
from app.infrastructure.database import close_db, init_db
from app.infrastructure.google_oauth import GoogleOAuthClient
from app.infrastructure.logging import setup_logging
from app.services.tool_seeder import ToolSeederService

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    settings = get_settings()

    # 1. Validate ENCRYPTION_KEY — app refuses to start without it
    if not settings.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY is required but not set")
    app.state.encryption = SecretEncryption(settings.encryption_key)
    logger.info("startup.encryption_key_validated")

    # 2. Validate JWT_SECRET_KEY is present
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is required but not set")
    logger.info("startup.jwt_secret_validated")

    # 3. Health-check OneAI-Auth (HARD DEP — 3 retries, 2s backoff)
    auth_client = AuthClient()
    for attempt in range(1, 4):
        if await auth_client.health_check():
            logger.info("startup.auth_service_healthy")
            break
        logger.warning("startup.auth_service_unavailable", attempt=attempt)
        if attempt < 3:
            await asyncio.sleep(2)
    else:
        logger.error("startup.auth_service_unreachable")
        # Don't crash — auth service may come up later. Log the warning.

    # 4. Initialize database engine + session factory
    await init_db(app)
    logger.info("startup.database_initialized")

    # 5. Seed pre-built tool catalog (idempotent — safe to re-run)
    seeder = ToolSeederService(app.state.session_factory)
    seed_result = await seeder.seed()
    logger.info("startup.tool_catalog_seeded", **seed_result)

    # 6. Initialize Google OAuth client (optional — disabled if not configured)
    if settings.google_client_id and settings.google_client_secret:
        app.state.google_oauth_client = GoogleOAuthClient(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        logger.info("startup.google_oauth_configured")
    else:
        app.state.google_oauth_client = None
        logger.info("startup.google_oauth_not_configured")

    # 7. Redis initialization (deferred until Redis service module is built)

    # 8. Register framework adapters
    registry = AdapterRegistry()
    registry.register(DeepAgentsAdapter())
    app.state.adapter_registry = registry
    logger.info("startup.adapters_registered", adapters=registry.list_adapters())

    logger.info("startup.complete", version=__version__)
    yield

    # --- Shutdown ---
    await close_db(app)
    logger.info("shutdown.database_closed")
    logger.info("shutdown.complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="OneAI-Cortex",
        description="Open-source AI agent builder platform",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    # CORS — allow the UI dev server to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",   # OneAI-UI (Vite dev)
            "http://localhost:4173",   # OneAI-UI (Vite preview)
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    register_exception_handlers(app)
    setup_logging(log_level="INFO", json_output=False)
    return app


app = create_app()
