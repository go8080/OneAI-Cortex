"""Maps domain exceptions to HTTP responses. The ONLY place HTTP status codes meet exceptions."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AdapterError,
    AgentExecutionError,
    AppError,
    AuthenticationError,
    AuthorizationError,
    DuplicateEntityError,
    EncryptionError,
    EntityNotFoundError,
    MCPConnectionError,
    ValidationError,
)

STATUS_MAP: dict[type[AppError], int] = {
    EntityNotFoundError: 404,
    DuplicateEntityError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    ValidationError: 422,
    EncryptionError: 500,
    AdapterError: 502,
    AgentExecutionError: 500,
    MCPConnectionError: 502,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        status_code = STATUS_MAP.get(type(exc), 500)
        return JSONResponse(
            status_code=status_code,
            content={"error": exc.code, "message": exc.message},
        )
