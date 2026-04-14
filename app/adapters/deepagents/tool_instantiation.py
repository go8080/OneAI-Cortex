"""Shared tool instantiation logic for LangChain tools.

Many LangChain community tools require an ``api_wrapper`` object.
This module centralises the wrapper-aware instantiation logic so both
the runtime resolver and the playground test service use the same code.

Google OAuth tools (auth_type="google_oauth") use a different path:
they receive an access token and build Google API credentials directly,
rather than reading API keys from environment variables.
"""

from __future__ import annotations

import importlib
import os
from typing import Any

import structlog

from app.services.seed_data import TOOL_CATALOG

__all__ = ["instantiate_tool", "instantiate_google_oauth_tools", "TOOL_META"]

logger = structlog.get_logger(__name__)

# ── Wrapper registry ────────────────────────────────────────────────────
# Maps tool name → wrapper class path.  Tools NOT in this map are
# instantiated directly (no wrapper needed).

_WRAPPER_MAP: dict[str, str] = {
    # Search
    "brave_search": "langchain_community.tools.brave_search.tool.BraveSearchWrapper",
    "searx_search": "langchain_community.utilities.searx_search.SearxSearchWrapper",
    "ddg_search": "langchain_community.utilities.duckduckgo_search.DuckDuckGoSearchAPIWrapper",
    "ddg_search_results": "langchain_community.utilities.duckduckgo_search.DuckDuckGoSearchAPIWrapper",
    # Research
    "arxiv_search": "langchain_community.utilities.arxiv.ArxivAPIWrapper",
    "pubmed_search": "langchain_community.utilities.pubmed.PubMedAPIWrapper",
    "wikipedia_search": "langchain_community.utilities.wikipedia.WikipediaAPIWrapper",
    "google_scholar_search": "langchain_community.utilities.google_scholar.GoogleScholarAPIWrapper",
    "stackexchange_search": "langchain_community.utilities.stackexchange.StackExchangeAPIWrapper",
    # Weather & Location
    "openweathermap": "langchain_community.utilities.openweathermap.OpenWeatherMapAPIWrapper",
    "google_places": "langchain_community.utilities.google_places_api.GooglePlacesAPIWrapper",
    # Finance / Media / Utility (SerpAPI-based)
    "google_finance": "langchain_community.utilities.google_finance.GoogleFinanceAPIWrapper",
    "google_trends": "langchain_community.utilities.google_trends.GoogleTrendsAPIWrapper",
    "google_lens": "langchain_community.utilities.google_lens.GoogleLensAPIWrapper",
    "google_jobs": "langchain_community.utilities.google_jobs.GoogleJobsAPIWrapper",
    # Science
    "wolfram_alpha": "langchain_community.utilities.wolfram_alpha.WolframAlphaAPIWrapper",
    # Utility
    "merriam_webster": "langchain_community.utilities.merriam_webster.MerriamWebsterAPIWrapper",
}

# ── Metadata lookup ─────────────────────────────────────────────────────
# Flat name → catalog entry for quick lookup by both resolver and service.

TOOL_META: dict[str, dict[str, Any]] = {}
for _cat, _tools in TOOL_CATALOG.items():
    for _tool_def in _tools:
        TOOL_META[_tool_def["name"]] = _tool_def


def _import_class(fqn: str) -> type:
    """Import a class from its fully qualified module path."""
    module_path, class_name = fqn.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def instantiate_tool(
    tool_name: str,
    *,
    api_keys: dict[str, str] | None = None,
    set_env: bool = False,
) -> Any:
    """Instantiate a LangChain tool by catalog name.

    Args:
        tool_name: Tool name from the catalog (e.g. ``"wikipedia_search"``).
        api_keys: Optional dict of API keys.  When *set_env* is True these
            are injected into ``os.environ`` (upper-cased) before
            instantiation — this is how LangChain tools pick up keys.
            When *set_env* is False the keys are passed as constructor
            kwargs to the wrapper / tool class.
        set_env: If True, set api_keys as env vars instead of kwargs.

    Returns:
        An instantiated LangChain BaseTool.

    Raises:
        KeyError: If *tool_name* is not in the catalog.
        ImportError / TypeError: If the class cannot be imported / instantiated.
    """
    meta = TOOL_META.get(tool_name)
    if meta is None:
        raise KeyError(f"Unknown tool: {tool_name}")

    langchain_class = meta["langchain_class"]
    keys = api_keys or {}

    # Optionally inject keys into env (adapter runtime path)
    env_backup: dict[str, str | None] = {}
    if set_env and keys:
        for k, v in keys.items():
            env_key = k.upper()
            env_backup[env_key] = os.environ.get(env_key)
            os.environ[env_key] = v

    try:
        tool_cls = _import_class(langchain_class)
        wrapper_fqn = _WRAPPER_MAP.get(tool_name)

        if wrapper_fqn:
            # Tool needs an api_wrapper
            wrapper_cls = _import_class(wrapper_fqn)
            if set_env:
                wrapper = wrapper_cls()
            else:
                wrapper = wrapper_cls(**keys) if keys else wrapper_cls()
            return tool_cls(api_wrapper=wrapper)
        else:
            # Direct instantiation (e.g. TavilySearchResults)
            if set_env:
                return tool_cls()
            else:
                return tool_cls(**keys) if keys else tool_cls()
    finally:
        # Restore env if we modified it
        if set_env and env_backup:
            for k, original in env_backup.items():
                if original is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = original


# ── Google OAuth tool names (grouped by service) ───────────────────────

_GMAIL_TOOLS = {"gmail_send_message", "gmail_search", "gmail_get_message", "gmail_create_draft"}
_CALENDAR_TOOLS = {"google_calendar_list_events", "google_calendar_create_event"}
_DRIVE_TOOLS = {"google_drive_search", "google_drive_read"}
GOOGLE_OAUTH_TOOLS = _GMAIL_TOOLS | _CALENDAR_TOOLS | _DRIVE_TOOLS


def instantiate_google_oauth_tools(
    tool_names: list[str],
    access_token: str,
) -> list[Any]:
    """Instantiate Google OAuth tools that need an access token.

    Unlike regular tools (env vars or constructor kwargs), Google OAuth tools
    receive a fresh access token from Connected Services and build Google API
    credentials directly.

    Args:
        tool_names: Tool names that have auth_type="google_oauth".
        access_token: Fresh Google OAuth access token (ya29.xxx).

    Returns:
        List of instantiated BaseTool objects.
    """
    from app.adapters.deepagents.google_tools import (
        build_gmail_tools,
        GoogleCalendarCreateEvent,
        GoogleCalendarListEvents,
        GoogleDriveRead,
        GoogleDriveSearch,
    )

    resolved: list[Any] = []
    needs_gmail = bool(_GMAIL_TOOLS & set(tool_names))
    needs_calendar = bool(_CALENDAR_TOOLS & set(tool_names))
    needs_drive = bool(_DRIVE_TOOLS & set(tool_names))

    # Gmail — LangChain's built-in tools share one api_resource
    if needs_gmail:
        gmail_tools = build_gmail_tools(access_token)
        # Filter to only the requested Gmail tools
        gmail_name_map = {t.name: t for t in gmail_tools}
        for name in tool_names:
            if name in _GMAIL_TOOLS and name in gmail_name_map:
                resolved.append(gmail_name_map[name])
            elif name in _GMAIL_TOOLS:
                # LangChain tool names may differ — add all Gmail tools
                pass
        # If specific names didn't match, include all built Gmail tools
        if needs_gmail and not any(t.name in _GMAIL_TOOLS for t in resolved):
            resolved.extend(gmail_tools)

    # Calendar — custom tools with access_token attribute
    if needs_calendar:
        for name in tool_names:
            if name == "google_calendar_list_events":
                resolved.append(GoogleCalendarListEvents(access_token=access_token))
            elif name == "google_calendar_create_event":
                resolved.append(GoogleCalendarCreateEvent(access_token=access_token))

    # Drive — custom tools with access_token attribute
    if needs_drive:
        for name in tool_names:
            if name == "google_drive_search":
                resolved.append(GoogleDriveSearch(access_token=access_token))
            elif name == "google_drive_read":
                resolved.append(GoogleDriveRead(access_token=access_token))

    logger.info(
        "google_oauth_tools.resolved",
        requested=tool_names,
        resolved=[t.name for t in resolved],
    )
    return resolved
