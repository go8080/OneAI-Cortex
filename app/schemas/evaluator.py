"""Pydantic schemas for evaluator endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

__all__ = [
    "EvalResultResponse",
    "EvalRunResponse",
    "TestCaseCreate",
    "TestCaseResponse",
    "TestSuiteCreate",
    "TestSuiteResponse",
]


class TestSuiteCreate(BaseModel):
    """Request body for creating a test suite."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    scoring_method: str = "contains"


class TestSuiteResponse(BaseModel):
    """Test suite in API responses."""

    id: UUID
    agent_id: UUID
    name: str
    description: str | None
    scoring_method: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestCaseCreate(BaseModel):
    """Request body for creating a test case."""

    name: str = Field(..., min_length=1, max_length=255)
    input_message: str
    expected_output: str | None = None
    tags: list[str] = Field(default_factory=list)


class TestCaseResponse(BaseModel):
    """Test case in API responses."""

    id: UUID
    test_suite_id: UUID
    name: str
    input_message: str
    expected_output: str | None
    tags: list[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalRunResponse(BaseModel):
    """Evaluation run in API responses."""

    id: UUID
    test_suite_id: UUID
    agent_id: UUID
    agent_version: int
    status: str
    metrics: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalResultResponse(BaseModel):
    """Single test case result in API responses."""

    id: UUID
    eval_run_id: UUID
    test_case_id: UUID
    actual_output: str
    score: float
    passed: bool
    latency_ms: int
    token_count: int | None

    model_config = {"from_attributes": True}
