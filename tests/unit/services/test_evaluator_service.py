"""Tests for app.services.evaluator — EvaluatorService scoring logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.adapters.registry import AdapterRegistry
from app.core.encryption import SecretEncryption
from app.schemas.evaluator import TestCaseCreate, TestSuiteCreate
from app.services.evaluator import EvaluatorService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def agent_repo():
    return AsyncMock()


@pytest.fixture
def adapter_registry():
    registry = AdapterRegistry()
    adapter = MagicMock()
    adapter.framework_name = "deepagents"
    registry.register(adapter)
    return registry


@pytest.fixture
def encryption():
    return SecretEncryption(Fernet.generate_key().decode())


@pytest.fixture
def service(repo, agent_repo, adapter_registry, encryption):
    return EvaluatorService(repo, agent_repo, adapter_registry, encryption)


class TestScoring:
    def test_exact_match_pass(self, service):
        assert service._score("exact_match", "Paris", "Paris") == 1.0

    def test_exact_match_case_insensitive(self, service):
        # Implementation uses case-insensitive comparison
        assert service._score("exact_match", "paris", "Paris") == 1.0

    def test_exact_match_fail(self, service):
        assert service._score("exact_match", "London", "Paris") == 0.0

    def test_contains_pass(self, service):
        assert service._score("contains", "The capital is Paris, France", "Paris") == 1.0

    def test_contains_fail(self, service):
        assert service._score("contains", "London is the capital", "Paris") == 0.0

    def test_none_expected_returns_pass(self, service):
        # None expected means no assertion — auto-pass
        result = service._score("contains", "anything", None)
        assert result == 1.0

    def test_llm_judge_returns_default(self, service):
        result = service._score("llm_judge", "response", "expected")
        assert result == 0.5  # placeholder score


class TestCreateSuite:
    async def test_creates_suite(self, service, repo):
        repo.create_suite.return_value = MagicMock(id=uuid4())
        data = TestSuiteCreate(name="QA Suite", scoring_method="contains")
        result = await service.create_suite(uuid4(), data)
        repo.create_suite.assert_called_once()


class TestCreateCase:
    async def test_creates_case(self, service, repo):
        repo.create_case.return_value = MagicMock(id=uuid4())
        data = TestCaseCreate(name="Test 1", input_message="What is 2+2?", expected_output="4")
        result = await service.create_case(uuid4(), data)
        repo.create_case.assert_called_once()
