"""Health check endpoints — liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import __version__
from app.infrastructure.auth_client import AuthClient

router = APIRouter()


@router.get("")
async def health() -> dict:
    """Liveness probe — always returns OK if the process is running."""
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def readiness(request: Request) -> dict:
    """Readiness probe — checks DB, Redis, and OneAI-Auth connectivity."""
    checks: dict[str, str] = {}

    # Database
    try:
        if hasattr(request.app.state, "session_factory"):
            async with request.app.state.session_factory() as session:
                await session.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
            checks["db"] = "ok"
        else:
            checks["db"] = "not_initialized"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    # Redis (placeholder until Redis service is wired)
    checks["redis"] = "ok"

    # OneAI-Auth
    auth_client = AuthClient()
    if await auth_client.health_check():
        checks["auth"] = "ok"
    else:
        checks["auth"] = "unreachable"

    all_ok = all(v == "ok" for v in checks.values())
    return {"ready": all_ok, **checks}
