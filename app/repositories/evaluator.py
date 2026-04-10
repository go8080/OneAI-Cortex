"""Evaluator repository — data access for test suites, test cases, eval runs, and results."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import EvalResult, EvalRun, TestCase, TestSuite

__all__ = ["EvaluatorRepository"]


class EvaluatorRepository:
    """Data access for the evaluation system."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # === Test Suites ===

    async def create_suite(self, data: dict[str, Any]) -> TestSuite:
        instance = TestSuite(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_suite(self, suite_id: UUID) -> TestSuite | None:
        stmt = select(TestSuite).where(TestSuite.id == suite_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_suites(self, agent_id: UUID) -> list[TestSuite]:
        stmt = select(TestSuite).where(TestSuite.agent_id == agent_id).order_by(TestSuite.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # === Test Cases ===

    async def create_case(self, data: dict[str, Any]) -> TestCase:
        instance = TestCase(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def list_cases(self, suite_id: UUID) -> list[TestCase]:
        stmt = select(TestCase).where(TestCase.test_suite_id == suite_id).order_by(TestCase.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # === Eval Runs ===

    async def create_run(self, data: dict[str, Any]) -> EvalRun:
        instance = EvalRun(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get_run(self, run_id: UUID) -> EvalRun | None:
        stmt = select(EvalRun).where(EvalRun.id == run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_run(self, run_id: UUID, data: dict[str, Any]) -> EvalRun | None:
        run = await self.get_run(run_id)
        if run is None:
            return None
        for key, value in data.items():
            setattr(run, key, value)
        await self._session.flush()
        return run

    async def list_runs(self, agent_id: UUID) -> list[EvalRun]:
        stmt = (
            select(EvalRun)
            .where(EvalRun.agent_id == agent_id)
            .order_by(EvalRun.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # === Eval Results ===

    async def create_result(self, data: dict[str, Any]) -> EvalResult:
        instance = EvalResult(**data)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def list_results(self, run_id: UUID) -> list[EvalResult]:
        stmt = select(EvalResult).where(EvalResult.eval_run_id == run_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
