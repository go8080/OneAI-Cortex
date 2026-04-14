"""Google OAuth tool builders — Gmail, Calendar, Drive.

These tools use a Google OAuth access token (from Connected Services) to call
Google APIs. The token is injected at runtime by the adapter, not via env vars.

Gmail tools use LangChain's built-in GmailXxx classes.
Calendar and Drive tools are custom BaseTool implementations that call the
Google API directly via googleapiclient.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import Field

import structlog

__all__ = [
    "build_google_api_resource",
    "build_gmail_tools",
    "GoogleCalendarListEvents",
    "GoogleCalendarCreateEvent",
    "GoogleDriveSearch",
    "GoogleDriveRead",
]

logger = structlog.get_logger(__name__)


def build_google_api_resource(access_token: str, service: str, version: str):
    """Build a Google API resource from an OAuth access token.

    Args:
        access_token: Fresh Google OAuth access token (ya29.xxx).
        service: Google API service name (gmail, calendar, drive).
        version: API version (v1, v3).

    Returns:
        A googleapiclient Resource object ready to make API calls.
    """
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(token=access_token)
    return build(service, version, credentials=creds, cache_discovery=False)


def build_gmail_tools(access_token: str) -> list[BaseTool]:
    """Build LangChain Gmail tools from a Google OAuth access token."""
    from langchain_community.tools.gmail import (
        GmailCreateDraft,
        GmailGetMessage,
        GmailGetThread,
        GmailSearch,
        GmailSendMessage,
    )

    api_resource = build_google_api_resource(access_token, "gmail", "v1")

    return [
        GmailSearch(api_resource=api_resource),
        GmailGetMessage(api_resource=api_resource),
        GmailGetThread(api_resource=api_resource),
        GmailCreateDraft(api_resource=api_resource),
        GmailSendMessage(api_resource=api_resource),
    ]


# ── Google Calendar Tools ─────────────────────────────────────────────


class GoogleCalendarListEvents(BaseTool):
    """List upcoming events from Google Calendar."""

    name: str = "google_calendar_list_events"
    description: str = "List upcoming events from Google Calendar. Returns event summaries, start/end times."
    access_token: str = ""

    def _run(self, max_results: int = 10, time_min: str | None = None) -> str:
        service = build_google_api_resource(self.access_token, "calendar", "v3")
        now = time_min or datetime.now(UTC).isoformat()

        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = result.get("items", [])
        if not events:
            return "No upcoming events found."

        lines = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            summary = event.get("summary", "(no title)")
            lines.append(f"- {summary}: {start} to {end}")

        return "\n".join(lines)


class GoogleCalendarCreateEvent(BaseTool):
    """Create a new event on Google Calendar."""

    name: str = "google_calendar_create_event"
    description: str = "Create a new event on Google Calendar with a title, start time, and end time."
    access_token: str = ""

    def _run(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
    ) -> str:
        service = build_google_api_resource(self.access_token, "calendar", "v3")

        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }
        if description:
            event_body["description"] = description

        created = service.events().insert(calendarId="primary", body=event_body).execute()
        return f"Event created: {created.get('summary')} (ID: {created.get('id')})"


# ── Google Drive Tools ────────────────────────────────────────────────


class GoogleDriveSearch(BaseTool):
    """Search for files in Google Drive."""

    name: str = "google_drive_search"
    description: str = "Search for files in Google Drive by name or query. Returns file names, IDs, and types."
    access_token: str = ""

    def _run(self, query: str) -> str:
        service = build_google_api_resource(self.access_token, "drive", "v3")

        result = (
            service.files()
            .list(
                q=f"name contains '{query}'",
                pageSize=10,
                fields="files(id, name, mimeType, modifiedTime)",
            )
            .execute()
        )

        files = result.get("files", [])
        if not files:
            return f"No files found matching '{query}'."

        lines = []
        for f in files:
            lines.append(
                f"- {f['name']} (type: {f['mimeType']}, id: {f['id']})"
            )

        return "\n".join(lines)


class GoogleDriveRead(BaseTool):
    """Read a file's content from Google Drive."""

    name: str = "google_drive_read"
    description: str = "Read a file's text content from Google Drive by file ID. Works with Google Docs, Sheets (as CSV), and plain text files."
    access_token: str = ""

    def _run(self, file_id: str) -> str:
        service = build_google_api_resource(self.access_token, "drive", "v3")

        # Get file metadata to determine type
        meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
        mime = meta.get("mimeType", "")

        # Google Docs → export as plain text
        if mime == "application/vnd.google-apps.document":
            content = (
                service.files()
                .export(fileId=file_id, mimeType="text/plain")
                .execute()
            )
            return content.decode("utf-8") if isinstance(content, bytes) else str(content)

        # Google Sheets → export as CSV
        if mime == "application/vnd.google-apps.spreadsheet":
            content = (
                service.files()
                .export(fileId=file_id, mimeType="text/csv")
                .execute()
            )
            return content.decode("utf-8") if isinstance(content, bytes) else str(content)

        # Regular files → download content
        content = service.files().get_media(fileId=file_id).execute()
        return content.decode("utf-8") if isinstance(content, bytes) else str(content)
