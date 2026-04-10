"""Database engine, session factory, and connection pool configuration."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


async def init_db(app: FastAPI) -> None:
    """Initialize async database engine and session factory during startup."""
    settings = get_settings()
    app.state.engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        echo=settings.db_echo,
    )
    app.state.session_factory = async_sessionmaker(
        app.state.engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db(app: FastAPI) -> None:
    """Dispose database engine during shutdown."""
    if hasattr(app.state, "engine") and app.state.engine is not None:
        await app.state.engine.dispose()
