"""Checkpointer factory — creates AsyncSqliteSaver instances per session.

Each session gets its own SQLite file at data/checkpoints/{session_id}.db.
This keeps LangGraph's native checkpoint format and allows trivial cleanup.
"""

from __future__ import annotations

import os
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.config import get_settings

__all__ = ["get_checkpointer"]


async def get_checkpointer(session_id: str) -> AsyncSqliteSaver:
    """Create an AsyncSqliteSaver for the given session.

    The checkpoint directory is created on first call if it doesn't exist.
    """
    settings = get_settings()
    checkpoint_dir = Path(settings.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    db_path = checkpoint_dir / f"{session_id}.db"
    return AsyncSqliteSaver.from_conn_string(str(db_path))


def cleanup_expired_checkpoints(retention_days: int | None = None) -> int:
    """Remove checkpoint files older than retention_days. Returns count removed.

    Meant to be called from a periodic task or CLI command.
    """
    settings = get_settings()
    days = retention_days or settings.checkpoint_retention_days
    checkpoint_dir = Path(settings.checkpoint_dir)

    if not checkpoint_dir.exists():
        return 0

    import time

    cutoff = time.time() - (days * 86400)
    removed = 0

    for db_file in checkpoint_dir.glob("*.db"):
        if db_file.stat().st_mtime < cutoff:
            db_file.unlink()
            removed += 1

    return removed
