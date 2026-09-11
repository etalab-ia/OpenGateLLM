from unittest.mock import create_autospec

import pytest

from api.domain.model.entities import HealthStatus, ModelHealthStatus, Models
from api.domain.model.errors import StatusCodeModelError
from api.domain.provider import ProviderClient, ProviderQoS, ProviderRepository
from api.domain.provider.entities import ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.domain.role.entities import Limit, LimitType
from api.domain.router import RouterRepository
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess
from api.utils.variables import EndpointRoute


@pytest.fixture
def mock_provider_client():
    return create_autospec(ProviderClient, instance=True, spec_set=True)


@pytest.fixture
def mock_provider_qos():
    return create_autospec(ProviderQoS, instance=True, spec_set=True)


@pytest.fixture
def mock_router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_provider_repository():
    return create_autospec(ProviderRepository, instance=True, spec_set=True)


@pytest.fixture
def command():
    user = AuthenticatedUserFactory(
        id=1,
        limits=[Limit(router_id=1, value=100, type=LimitType.RPM)],
        permissions=[],
    )
    return GetHealthModelsCommand(authenticated_user=user)


@pytest.fixture
def use_case(mock_provider_client, mock_provider_qos, mock_router_repository, mock_provider_repository):
    return GetHealthModelsUseCase(
        provider_client=mock_provider_client,
        provider_qos=mock_provider_qos,
        router_repository=mock_router_repository,
        provider_repository=mock_provider_repository,
    )


@pytest.fixture(autouse=True)
def configure_healthy_provider(mock_provider_client):
    mock_provider_client.forward.return_value = ProviderResponse(id="request-1", data=Models(data=[]))


@pytest.mark.asyncio
class TestGetHealthModelsUseCase:
    async def test_should_return_green_for_live_uncapped_provider(
        self,
        use_case,
        command,
        mock_router_repository,
        mock_provider_repository,
        mock_provider_qos,
        mock_provider_client,
    ):
        # Arrange
        router = RouterFactory(id=1, name="model", providers=1)
        provider = ProviderFactory(id=1, router_id=router.id, qos_limit=None, timeout=300)
        mock_router_repository.get_all_routers.return_value = [router]
        mock_provider_repository.get_all_providers.return_value = [provider]
        mock_provider_qos.get_loads.return_value = {provider.id: 12}

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result == GetHealthModelsUseCaseSuccess(models=[ModelHealthStatus(id="model", status=HealthStatus.GREEN)])
        forwarded_provider = mock_provider_client.forward.await_args.kwargs["provider"]
        assert forwarded_provider.timeout == 4
        assert provider.timeout == 300
        assert mock_provider_client.forward.await_args.kwargs["request"].endpoint == EndpointRoute.MODELS

    @pytest.mark.parametrize(
        ("qos_limit", "load", "expected_status"),
        [
            (0, 0, HealthStatus.RED),
            (20, 18, HealthStatus.GREEN),
            (20, 19, HealthStatus.ORANGE),
            (20, 20, HealthStatus.RED),
            (4, 3, HealthStatus.GREEN),
            (4, 4, HealthStatus.RED),
        ],
    )
    async def test_should_compute_saturation_from_qos_load(
        self,
        use_case,
        command,
        mock_router_repository,
        mock_provider_repository,
        mock_provider_qos,
        qos_limit,
        load,
        expected_status,
    ):
        # Arrange
        router = RouterFactory(id=1, name="model", providers=1)
        provider = ProviderFactory(id=1, router_id=router.id, qos_limit=qos_limit)
        mock_router_repository.get_all_routers.return_value = [router]
        mock_provider_repository.get_all_providers.return_value = [provider]
        mock_provider_qos.get_loads.return_value = {provider.id: load}

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result.models[0].status == expected_status

    async def test_should_return_red_when_liveness_probe_fails(
        self,
        use_case,
        command,
        mock_router_repository,
        mock_provider_repository,
        mock_provider_qos,
        mock_provider_client,
    ):
        # Arrange
        router = RouterFactory(id=1, name="model", providers=1)
        provider = ProviderFactory(id=1, router_id=router.id)
        mock_router_repository.get_all_routers.return_value = [router]
        mock_provider_repository.get_all_providers.return_value = [provider]
        mock_provider_qos.get_loads.return_value = {provider.id: 0}
        mock_provider_client.forward.return_value = StatusCodeModelError(status_code=500, detail="failed")

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result.models[0].status == HealthStatus.RED

    async def test_should_treat_invalid_models_payload_as_live(
        self,
        use_case,
        command,
        mock_router_repository,
        mock_provider_repository,
        mock_provider_qos,
        mock_provider_client,
    ):
        # Arrange
        router = RouterFactory(id=1, name="model", providers=1)
        provider = ProviderFactory(id=1, router_id=router.id)
        mock_router_repository.get_all_routers.return_value = [router]
        mock_provider_repository.get_all_providers.return_value = [provider]
        mock_provider_qos.get_loads.return_value = {provider.id: 0}
        mock_provider_client.forward.return_value = ProviderAdapterValidationResponseError(provider_type=provider.type, errors=[])

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result.models[0].status == HealthStatus.GREEN

    async def test_should_aggregate_best_provider_status(
        self,
        use_case,
        command,
        mock_router_repository,
        mock_provider_repository,
        mock_provider_qos,
        mock_provider_client,
    ):
        # Arrange
        router = RouterFactory(id=1, name="model", providers=2)
        red_provider = ProviderFactory(id=1, router_id=router.id, qos_limit=1)
        green_provider = ProviderFactory(id=2, router_id=router.id, qos_limit=20)
        mock_router_repository.get_all_routers.return_value = [router]
        mock_provider_repository.get_all_providers.return_value = [red_provider, green_provider]
        mock_provider_qos.get_loads.return_value = {red_provider.id: 1, green_provider.id: 0}
        mock_provider_client.forward.side_effect = [
            StatusCodeModelError(status_code=500, detail="failed"),
            ProviderResponse(id="request-2", data=Models(data=[])),
        ]

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result.models[0].status == HealthStatus.GREEN

    async def test_should_filter_inaccessible_routers(
        self,
        use_case,
        command,
        mock_router_repository,
        mock_provider_repository,
        mock_provider_qos,
    ):
        # Arrange
        inaccessible = RouterFactory(id=2, name="hidden", providers=1)
        provider = ProviderFactory(id=2, router_id=inaccessible.id)
        mock_router_repository.get_all_routers.return_value = [inaccessible]
        mock_provider_repository.get_all_providers.return_value = [provider]
        mock_provider_qos.get_loads.return_value = {provider.id: 0}

        # Act
        result = await use_case.execute(command)

        # Assert
        assert result.models == []
