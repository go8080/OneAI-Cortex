"""Tool resolver — converts tool name strings to LangChain BaseTool instances."""

from __future__ import annotations

from typing import Any

import structlog

from app.adapters.deepagents.tool_instantiation import (
    GOOGLE_OAUTH_TOOLS,
    instantiate_google_oauth_tools,
    instantiate_tool,
)

__all__ = ["resolve_tools"]

logger = structlog.get_logger(__name__)


def resolve_tools(
    tool_names: list[str],
    *,
    google_access_token: str | None = None,
) -> list[Any]:
    """Resolve tool name strings to instantiated LangChain BaseTool objects.

    Looks up each name in the pre-built TOOL_CATALOG. Unknown names are
    logged as warnings and skipped — the agent will run without them.

    Google OAuth tools (gmail, calendar, drive) are resolved separately
    using a fresh access token from Connected Services.

    Args:
        tool_names: List of tool name strings from agent config.
        google_access_token: Fresh Google OAuth token for google_oauth tools.

    Returns:
        List of instantiated BaseTool objects (unknown names excluded).
    """
    # Split into regular tools and Google OAuth tools
    regular_names = []
    google_names = []

    for name in tool_names:
        if name in GOOGLE_OAUTH_TOOLS:
            google_names.append(name)
        else:
            regular_names.append(name)

    resolved = []

    # Resolve regular tools (env vars already set by adapter)
    for name in regular_names:
        try:
            instance = instantiate_tool(name, set_env=False)
            resolved.append(instance)
            logger.debug("tool_resolver.resolved", tool_name=name)
        except KeyError:
            logger.warning("tool_resolver.unknown_tool", tool_name=name)
        except Exception as exc:
            logger.warning(
                "tool_resolver.instantiation_failed",
                tool_name=name,
                error=str(exc),
            )

    # Resolve Google OAuth tools (need access token, not env vars)
    if google_names:
        if google_access_token:
            try:
                google_tools = instantiate_google_oauth_tools(
                    google_names, google_access_token
                )
                resolved.extend(google_tools)
            except Exception as exc:
                logger.warning(
                    "tool_resolver.google_oauth_failed",
                    tools=google_names,
                    error=str(exc),
                )
        else:
            logger.warning(
                "tool_resolver.google_oauth_no_token",
                tools=google_names,
                message="Google OAuth tools requested but no access token provided. "
                "User must connect Google in Connected Services.",
            )

    return resolved
