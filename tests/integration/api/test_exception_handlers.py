"""Tests for exception handler mapping."""

from __future__ import annotations

import pytest

from app.api.exception_handlers import STATUS_MAP
from app.core.exceptions import (
    AdapterError,
    AgentExecutionError,
    AuthenticationError,
    AuthorizationError,
    DuplicateEntityError,
    EncryptionError,
    EntityNotFoundError,
    MCPConnectionError,
    ValidationError,
)


class TestStatusMap:
    def test_entity_not_found_is_404(self):
        assert STATUS_MAP[EntityNotFoundError] == 404

    def test_duplicate_is_409(self):
        assert STATUS_MAP[DuplicateEntityError] == 409

    def test_auth_error_is_401(self):
        assert STATUS_MAP[AuthenticationError] == 401

    def test_authorization_is_403(self):
        assert STATUS_MAP[AuthorizationError] == 403

    def test_validation_is_422(self):
        assert STATUS_MAP[ValidationError] == 422

    def test_encryption_is_500(self):
        assert STATUS_MAP[EncryptionError] == 500

    def test_adapter_is_502(self):
        assert STATUS_MAP[AdapterError] == 502

    def test_execution_is_500(self):
        assert STATUS_MAP[AgentExecutionError] == 500

    def test_mcp_connection_is_502(self):
        assert STATUS_MAP[MCPConnectionError] == 502

    def test_all_exceptions_mapped(self):
        """Every concrete AppError subclass should be in the map."""
        assert len(STATUS_MAP) == 9
