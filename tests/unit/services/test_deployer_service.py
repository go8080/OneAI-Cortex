"""Tests for app.services.deployer — DeployerService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import EntityNotFoundError, ValidationError
from app.services.deployer import DeployerService


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def agent_repo():
    return AsyncMock()


@pytest.fixture
def service(repo, agent_repo):
    return DeployerService(repo, agent_repo)


class TestDeployAgent:
    async def test_creates_deployment(self, service, repo, agent_repo):
        agent = MagicMock(id=uuid4(), current_version=2)
        agent_repo.get_by_id.return_value = agent
        repo.create.return_value = MagicMock(id=uuid4())

        result = await service.deploy_agent(agent.id, uuid4(), "hosted")
        repo.create.assert_called_once()

    async def test_agent_not_found_raises(self, service, agent_repo):
        agent_repo.get_by_id.return_value = None
        with pytest.raises(EntityNotFoundError):
            await service.deploy_agent(uuid4(), uuid4(), "hosted")

    async def test_uses_specified_version(self, service, repo, agent_repo):
        agent = MagicMock(id=uuid4(), current_version=3)
        agent_repo.get_by_id.return_value = agent
        repo.create.return_value = MagicMock()

        await service.deploy_agent(agent.id, uuid4(), "hosted", agent_version=2)
        call_data = repo.create.call_args[0][0]
        assert call_data["agent_version"] == 2


class TestUndeploy:
    async def test_sets_status_to_stopped(self, service, repo):
        deployment = MagicMock(user_id=uuid4())
        repo.get_by_id.return_value = deployment
        repo.update.return_value = None

        await service.undeploy(uuid4(), deployment.user_id)
        repo.update.assert_called_once()


class TestListDeployments:
    async def test_returns_list(self, service, repo):
        repo.list_by_agent.return_value = [MagicMock(), MagicMock()]
        result = await service.list_deployments(uuid4())
        assert len(result) == 2
