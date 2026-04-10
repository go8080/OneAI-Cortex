"""Evaluation ORM models — test suites, test cases, eval runs, eval results."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = ["EvalResult", "EvalRun", "TestCase", "TestSuite"]


class TestSuite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A collection of test cases for evaluating an agent."""

    __tablename__ = "test_suites"

    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scoring_method: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="contains"
    )

    # Relationships
    test_cases: Mapped[list[TestCase]] = relationship(
        back_populates="test_suite", cascade="all, delete-orphan"
    )
    eval_runs: Mapped[list[EvalRun]] = relationship(
        back_populates="test_suite", cascade="all, delete-orphan"
    )


class TestCase(UUIDPrimaryKeyMixin, Base):
    """A single test input/expected output pair."""

    __tablename__ = "test_cases"

    test_suite_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_message: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    test_suite: Mapped[TestSuite] = relationship(back_populates="test_cases")


class EvalRun(UUIDPrimaryKeyMixin, Base):
    """A single evaluation run of an agent against a test suite."""

    __tablename__ = "eval_runs"

    test_suite_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    agent_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    test_suite: Mapped[TestSuite] = relationship(back_populates="eval_runs")
    results: Mapped[list[EvalResult]] = relationship(
        back_populates="eval_run", cascade="all, delete-orphan"
    )


class EvalResult(UUIDPrimaryKeyMixin, Base):
    """Result of running a single test case in an eval run."""

    __tablename__ = "eval_results"

    eval_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
    )
    test_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False
    )
    actual_output: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    eval_run: Mapped[EvalRun] = relationship(back_populates="results")
