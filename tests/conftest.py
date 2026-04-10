"""Shared test fixtures for OneAI-Cortex."""

from __future__ import annotations

import uuid as _uuid_mod
from datetime import UTC, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.registry import AdapterRegistry
from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.encryption import SecretEncryption
from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.models.base import Base

# ---------------------------------------------------------------------------
# Database fixtures (in-memory SQLite for unit/integration tests)
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _remap_jsonb_to_json(base):
    """Replace JSONB columns with JSON for SQLite compatibility in tests."""
    for table in base.metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = JSON()


@pytest.fixture
async def async_engine():
    """Create an in-memory async SQLite engine for tests."""
    _remap_jsonb_to_json(Base)
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Register PostgreSQL functions that SQLite lacks
    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_functions(dbapi_conn, connection_record):
        dbapi_conn.create_function("gen_random_uuid", 0, lambda: _uuid_mod.uuid4().hex)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a test database session that rolls back after each test."""
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------

TEST_USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TEST_USER_2_ID = UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def test_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=TEST_USER_ID, auth_method="jwt")


@pytest.fixture
def test_user_2() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=TEST_USER_2_ID, auth_method="jwt")


# ---------------------------------------------------------------------------
# Encryption fixtures
# ---------------------------------------------------------------------------

TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@pytest.fixture
def encryption() -> SecretEncryption:
    return SecretEncryption(TEST_ENCRYPTION_KEY)


# ---------------------------------------------------------------------------
# Adapter fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_adapter() -> MagicMock:
    """A mock framework adapter that satisfies the FrameworkAdapter protocol."""
    adapter = MagicMock()
    adapter.framework_name = "deepagents"
    adapter.adapter_version = "1.0.0"
    adapter.sdk_compatibility = ">=0.5.0,<1.0.0"
    adapter.supported_models = []
    adapter.validate_config = AsyncMock(return_value=MagicMock(valid=True, errors=[], warnings=[]))
    adapter.create_runtime = AsyncMock()
    adapter.execute = AsyncMock()
    adapter.resume_after_interrupt = AsyncMock()
    return adapter


@pytest.fixture
def adapter_registry(mock_adapter) -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(mock_adapter)
    return registry


# ---------------------------------------------------------------------------
# FastAPI test app + client
# ---------------------------------------------------------------------------


@pytest.fixture
async def app(async_engine, test_user, encryption, adapter_registry) -> FastAPI:
    """Create a test FastAPI app with overridden dependencies."""
    test_app = FastAPI()
    test_app.include_router(api_router)
    register_exception_handlers(test_app)

    # Store on app.state for endpoints that access it
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    test_app.state.session_factory = session_factory
    test_app.state.encryption = encryption
    test_app.state.adapter_registry = adapter_registry

    # Override dependencies
    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def override_get_current_user():
        return test_user

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    return test_app


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
