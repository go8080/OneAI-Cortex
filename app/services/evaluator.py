"""Evaluator service — business logic for test suites and evaluation runs."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog

from app.adapters.registry import AdapterRegistry
from app.adapters.types import AgentConfig
from app.core.constants import AgentEventType
from app.core.encryption import SecretEncryption
from app.core.exceptions import EntityNotFoundError
from app.repositories.agent import AgentRepository
from app.repositories.evaluator import EvaluatorRepository
from app.schemas.evaluator import TestCaseCreate, TestSuiteCreate

__all__ = ["EvaluatorService"]

logger = structlog.get_logger(__name__)


class EvaluatorService:
    """Orchestrates evaluation operations."""

    def __init__(
        self,
        repo: EvaluatorRepository,
        agent_repo: AgentRepository,
        adapter_registry: AdapterRegistry,
        encryption: SecretEncryption,
    ) -> None:
        self._repo = repo
        self._agents = agent_repo
        self._adapters = adapter_registry
        self._encryption = encryption

    # === Test Suites ===

    async def create_suite(self, agent_id: UUID, data: TestSuiteCreate) -> object:
        return await self._repo.create_suite({
            "agent_id": agent_id,
            "name": data.name,
            "description": data.description,
            "scoring_method": data.scoring_method,
        })

    async def list_suites(self, agent_id: UUID) -> list:
        return await self._repo.list_suites(agent_id)

    # === Test Cases ===

    async def create_case(self, suite_id: UUID, data: TestCaseCreate) -> object:
        suite = await self._repo.get_suite(suite_id)
        if suite is None:
            raise EntityNotFoundError("TestSuite", "id", suite_id)
        return await self._repo.create_case({
            "test_suite_id": suite_id,
            "name": data.name,
            "input_message": data.input_message,
            "expected_output": data.expected_output,
            "tags": data.tags,
        })

    async def list_cases(self, suite_id: UUID) -> list:
        return await self._repo.list_cases(suite_id)

    # === Eval Runs ===

    async def run_evaluation(self, agent_id: UUID, suite_id: UUID) -> object:
        """Execute an evaluation run against all test cases in a suite."""
        agent = await self._agents.get_by_id(agent_id)
        if agent is None:
            raise EntityNotFoundError("Agent", "id", agent_id)

        suite = await self._repo.get_suite(suite_id)
        if suite is None:
            raise EntityNotFoundError("TestSuite", "id", suite_id)

        version = await self._agents.get_latest_version(agent_id)
        if version is None:
            raise EntityNotFoundError("AgentVersion", "agent_id", agent_id)

        # Create eval run
        run = await self._repo.create_run({
            "test_suite_id": suite_id,
            "agent_id": agent_id,
            "agent_version": version.version,
            "status": "running",
            "started_at": datetime.now(UTC),
        })

        # Load config and decrypt keys
        config_dict = version.config
        user_api_keys = {}
        if config_dict.get("user_api_keys"):
            user_api_keys = self._encryption.decrypt_dict_values(config_dict["user_api_keys"])

        agent_config = AgentConfig(
            name=agent.name,
            model=config_dict.get("model", "anthropic:claude-sonnet-4-6"),
            system_prompt=config_dict.get("system_prompt", ""),
        )

        adapter = self._adapters.get(agent.framework)
        cases = await self._repo.list_cases(suite_id)

        passed_count = 0
        total_latency = 0

        for case in cases:
            start = time.monotonic()
            runtime = await adapter.create_runtime(agent_config, user_api_keys)

            full_output = ""
            async for event in adapter.execute(
                runtime, [{"role": "user", "content": case.input_message}]
            ):
                if event.type == AgentEventType.MESSAGE:
                    full_output += event.content

            latency_ms = int((time.monotonic() - start) * 1000)
            total_latency += latency_ms

            score = self._score(suite.scoring_method, full_output, case.expected_output)
            is_passed = score >= 0.5

            if is_passed:
                passed_count += 1

            await self._repo.create_result({
                "eval_run_id": run.id,
                "test_case_id": case.id,
                "actual_output": full_output,
                "score": score,
                "passed": is_passed,
                "latency_ms": latency_ms,
            })

        # Update run with metrics
        total = len(cases) or 1
        await self._repo.update_run(run.id, {
            "status": "completed",
            "completed_at": datetime.now(UTC),
            "metrics": {
                "pass_rate": passed_count / total,
                "avg_latency_ms": total_latency / total,
                "total_cases": len(cases),
                "passed": passed_count,
            },
        })

        return await self._repo.get_run(run.id)

    def _score(self, method: str, actual: str, expected: str | None) -> float:
        """Score actual output against expected."""
        if expected is None:
            return 1.0
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        if method == "exact_match":
            return 1.0 if actual_lower == expected_lower else 0.0
        if method == "contains":
            return 1.0 if expected_lower in actual_lower else 0.0
        # llm_judge — deferred, return 0.5 as placeholder
        return 0.5

    async def list_runs(self, agent_id: UUID) -> list:
        return await self._repo.list_runs(agent_id)

    async def get_results(self, run_id: UUID) -> list:
        return await self._repo.list_results(run_id)
