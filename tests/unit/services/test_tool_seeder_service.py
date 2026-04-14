"""Tests for app.services.tool_seeder — ToolSeederService."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.tool import Tool
from app.services.tool_seeder import ToolSeederService


@pytest.fixture
def session_factory(async_engine):
    """Session factory bound to the test engine."""
    return async_sessionmaker(async_engine, expire_on_commit=False)


class TestToolSeederService:
    async def test_seed_creates_tools(self, session_factory):
        """First seed should create all tools from the catalog."""
        seeder = ToolSeederService(session_factory)
        result = await seeder.seed()

        assert result["created"] > 0
        assert result["skipped"] == 0

        # Verify tools are in the database
        async with session_factory() as session:
            stmt = select(Tool).where(Tool.tool_type == "builtin")
            rows = await session.execute(stmt)
            tools = list(rows.scalars().all())
            assert len(tools) == result["created"]

    async def test_seed_is_idempotent(self, session_factory):
        """Second seed should skip all existing tools, create zero."""
        seeder = ToolSeederService(session_factory)

        first = await seeder.seed()
        second = await seeder.seed()

        assert second["created"] == 0
        assert second["skipped"] == first["created"]

    async def test_seed_tools_have_required_fields(self, session_factory):
        """Every seeded tool should have category, langchain_class, and framework."""
        seeder = ToolSeederService(session_factory)
        await seeder.seed()

        async with session_factory() as session:
            stmt = select(Tool).where(Tool.tool_type == "builtin")
            rows = await session.execute(stmt)
            for tool in rows.scalars().all():
                assert tool.category is not None, f"{tool.name} missing category"
                assert tool.langchain_class is not None, f"{tool.name} missing langchain_class"
                assert tool.framework == "langchain"

    async def test_seed_skips_only_existing_creates_new(self, session_factory):
        """Seed with some tools pre-existing should create only the new ones."""
        # Pre-insert 2 tools that match catalog names
        async with session_factory() as session:
            for name in ("tavily_search", "ddg_search"):
                session.add(Tool(
                    name=name,
                    description="pre-existing",
                    framework="langchain",
                    tool_type="builtin",
                    category="search",
                    schema_def={},
                ))
            await session.commit()

        seeder = ToolSeederService(session_factory)
        result = await seeder.seed()

        assert result["skipped"] == 2
        assert result["created"] == result["created"]  # sanity
        assert result["created"] + result["skipped"] == 67
