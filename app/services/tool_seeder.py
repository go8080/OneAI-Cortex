"""Tool seeder service — idempotent startup seeding of the pre-built tool catalog."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.tool import Tool
from app.services.seed_data import TOOL_CATALOG

__all__ = ["ToolSeederService"]

logger = structlog.get_logger(__name__)


class ToolSeederService:
    """Seeds the tools table with curated LangChain tool definitions.

    Designed to run once during application startup. Idempotent — tools that
    already exist (matched by name) are skipped, so re-runs are safe.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def seed(self) -> dict[str, int]:
        """Insert pre-built tools from TOOL_CATALOG into the database.

        Returns:
            Summary dict with counts: {"created": N, "skipped": N}.
        """
        created = 0
        skipped = 0

        async with self._session_factory() as session:
            # Fetch all existing tool names in one query
            stmt = select(Tool.name)
            result = await session.execute(stmt)
            existing_names: set[str] = {row[0] for row in result.all()}

            for category, tools in TOOL_CATALOG.items():
                for tool_def in tools:
                    if tool_def["name"] in existing_names:
                        skipped += 1
                        continue

                    tool = Tool(
                        name=tool_def["name"],
                        description=tool_def["description"],
                        framework="langchain",
                        tool_type="builtin",
                        category=category,
                        schema_def=tool_def.get("schema_def", {}),
                        langchain_class=tool_def["langchain_class"],
                        required_keys=tool_def.get("required_keys", []),
                        input_schema=tool_def.get("input_schema", {}),
                        auth_type=tool_def.get("auth_type", "api_key"),
                    )
                    session.add(tool)
                    created += 1

            await session.commit()

        logger.info(
            "tool_seeder.complete",
            created=created,
            skipped=skipped,
            total_catalog=created + skipped,
        )
        return {"created": created, "skipped": skipped}
