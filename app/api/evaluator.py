"""Evaluator endpoints — test suites, test cases, and evaluation runs."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser
from app.dependencies import get_current_user, get_db
from app.repositories.agent import AgentRepository
from app.repositories.evaluator import EvaluatorRepository
from app.schemas.evaluator import (
    EvalResultResponse,
    EvalRunResponse,
    TestCaseCreate,
    TestCaseResponse,
    TestSuiteCreate,
    TestSuiteResponse,
)
from app.services.evaluator import EvaluatorService

router = APIRouter()


def _get_service(request: Request, db: AsyncSession = Depends(get_db)) -> EvaluatorService:
    return EvaluatorService(
        EvaluatorRepository(db),
        AgentRepository(db),
        request.app.state.adapter_registry,
        request.app.state.encryption,
    )


# === Test Suites ===


@router.post(
    "/{agent_id}/test-suites", response_model=TestSuiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_suite(
    agent_id: UUID,
    body: TestSuiteCreate,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> TestSuiteResponse:
    suite = await service.create_suite(agent_id, body)
    return TestSuiteResponse.model_validate(suite)


@router.get("/{agent_id}/test-suites", response_model=list[TestSuiteResponse])
async def list_test_suites(
    agent_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> list[TestSuiteResponse]:
    suites = await service.list_suites(agent_id)
    return [TestSuiteResponse.model_validate(s) for s in suites]


# === Test Cases ===


@router.post(
    "/{agent_id}/test-suites/{suite_id}/cases", response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_test_case(
    agent_id: UUID,
    suite_id: UUID,
    body: TestCaseCreate,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> TestCaseResponse:
    case = await service.create_case(suite_id, body)
    return TestCaseResponse.model_validate(case)


@router.get("/{agent_id}/test-suites/{suite_id}/cases", response_model=list[TestCaseResponse])
async def list_test_cases(
    agent_id: UUID,
    suite_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> list[TestCaseResponse]:
    cases = await service.list_cases(suite_id)
    return [TestCaseResponse.model_validate(c) for c in cases]


# === Eval Runs ===


@router.post(
    "/{agent_id}/test-suites/{suite_id}/run", response_model=EvalRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_evaluation(
    agent_id: UUID,
    suite_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> EvalRunResponse:
    run = await service.run_evaluation(agent_id, suite_id)
    return EvalRunResponse.model_validate(run)


@router.get("/{agent_id}/eval-runs", response_model=list[EvalRunResponse])
async def list_eval_runs(
    agent_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> list[EvalRunResponse]:
    runs = await service.list_runs(agent_id)
    return [EvalRunResponse.model_validate(r) for r in runs]


@router.get("/{agent_id}/eval-runs/{run_id}/results", response_model=list[EvalResultResponse])
async def get_eval_results(
    agent_id: UUID,
    run_id: UUID,
    _user: AuthenticatedUser = Depends(get_current_user),
    service: EvaluatorService = Depends(_get_service),
) -> list[EvalResultResponse]:
    results = await service.get_results(run_id)
    return [EvalResultResponse.model_validate(r) for r in results]
