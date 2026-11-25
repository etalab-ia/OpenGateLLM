from unittest.mock import create_autospec

import pytest

from api.domain.model.entities import HealthStatus, ModelHealthStatus
from api.domain.provider import ProviderConcurrencyLimiter, ProviderLimitsCannotBeEnforced
from api.domain.provider.entities import ProviderLoads
from api.domain.role.entities import Limit, LimitType
from api.domain.router import RouterRepository
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess, ProviderLivenessProbe


@pytest.fixture
def mock_provider_liveness_probe():
    provider_liveness_probe = create_autospec(ProviderLivenessProbe, instance=True, spec_set=True)
    provider_liveness_probe.is_live.return_value = True
    return provider_liveness_probe


@pytest.fixture
def mock_provider_concurrency_limiter():
    return create_autospec(ProviderConcurrencyLimiter, instance=True, spec_set=True)


@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_provider_liveness_probe, mock_provider_concurrency_limiter, mock_router_repository):
    return GetHealthModelsUseCase(
        provider_liveness_probe=mock_provider_liveness_probe,
        provider_concurrency_limiter=mock_provider_concurrency_limiter,
        router_repository=mock_router_repository,
    )


@pytest.fixture
def command():
    user = AuthenticatedUserFactory(id=1, limits=[Limit(router_id=1, value=100, type=LimitType.RPM)], permissions=[])
    return GetHealthModelsCommand(authenticated_user=user)


class TestGetHealthModelsUseCase:
    @pytest.mark.asyncio
    async def test_should_compute_each_provider_status_from_its_liveness_and_load(
        self, use_case, mock_provider_liveness_probe, mock_provider_concurrency_limiter, mock_router_repository, command
    ):
        # Arrange
        provider = ProviderFactory(id=1, router_id=1, qos_limit=20)
        mock_router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=[provider])]
        mock_provider_concurrency_limiter.read_loads.return_value = ProviderLoads(load_by_provider_id={1: 19})

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result == GetHealthModelsUseCaseSuccess(models=[ModelHealthStatus(id="gpt-4", status=HealthStatus.YELLOW)])
        mock_provider_concurrency_limiter.read_loads.assert_awaited_once_with(providers=[provider])
        mock_provider_liveness_probe.is_live.assert_awaited_once_with(provider=provider)

    @pytest.mark.asyncio
    async def test_should_return_the_best_provider_status_when_a_model_has_several_providers(
        self, use_case, mock_provider_liveness_probe, mock_provider_concurrency_limiter, mock_router_repository, command
    ):
        # Arrange
        mock_router_repository.get_all_routers.return_value = [
            RouterFactory(
                id=1,
                name="gpt-4",
                providers=[
                    ProviderFactory(id=1, router_id=1, qos_limit=20),
                    ProviderFactory(id=2, router_id=1, qos_limit=20),
                ],
            )
        ]
        mock_provider_concurrency_limiter.read_loads.return_value = ProviderLoads(load_by_provider_id={1: 0, 2: 0})
        mock_provider_liveness_probe.is_live.side_effect = [False, True]

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result.models == [ModelHealthStatus(id="gpt-4", status=HealthStatus.GREEN)]

    @pytest.mark.asyncio
    async def test_should_return_red_when_the_only_provider_is_not_live(
        self, use_case, mock_provider_liveness_probe, mock_provider_concurrency_limiter, mock_router_repository, command
    ):
        # Arrange
        mock_router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=[ProviderFactory(id=1, router_id=1)])]
        mock_provider_concurrency_limiter.read_loads.return_value = ProviderLoads(load_by_provider_id={1: 0})
        mock_provider_liveness_probe.is_live.return_value = False

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result.models == [ModelHealthStatus(id="gpt-4", status=HealthStatus.RED)]

    @pytest.mark.asyncio
    async def test_should_ignore_the_load_when_it_cannot_be_read(self, use_case, mock_provider_concurrency_limiter, mock_router_repository, command):
        # Arrange
        mock_router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="gpt-4", providers=[ProviderFactory(id=1, router_id=1, qos_limit=20)])
        ]
        mock_provider_concurrency_limiter.read_loads.return_value = ProviderLimitsCannotBeEnforced()

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result.models == [ModelHealthStatus(id="gpt-4", status=HealthStatus.GREEN)]

    @pytest.mark.asyncio
    async def test_should_skip_the_routers_without_providers_and_the_routers_the_user_cannot_access(
        self, use_case, mock_provider_liveness_probe, mock_provider_concurrency_limiter, mock_router_repository, command
    ):
        # Arrange
        accessible_provider = ProviderFactory(id=1, router_id=1)
        mock_router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="accessible", providers=[accessible_provider]),
            RouterFactory(id=2, name="forbidden", providers=[ProviderFactory(id=2, router_id=2)]),
            RouterFactory(id=3, name="no-providers", providers=[]),
        ]
        mock_provider_concurrency_limiter.read_loads.return_value = ProviderLoads(load_by_provider_id={1: 0, 2: 0})

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert [model.id for model in result.models] == ["accessible"]
        mock_provider_liveness_probe.is_live.assert_awaited_once_with(provider=accessible_provider)
