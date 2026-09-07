from unittest.mock import AsyncMock

import pytest

from api.domain.model.entities import HealthStatus, ModelHealthStatus, Models
from api.domain.model.errors import StatusCodeModelError
from api.domain.provider.entities import ProviderMetrics, ProviderResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationResponseError, UnsupportedProviderEndpointError
from api.domain.role.entities import Limit, LimitType
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess
from api.utils.variables import EndpointRoute

METRICS_TEXT = 'vllm:num_requests_running{model_name="my-model"} 0\nvllm:num_requests_waiting{model_name="my-model"} 0\n'


@pytest.fixture
def provider_client():
    return AsyncMock()


@pytest.fixture
def provider_metrics_logger():
    return AsyncMock()


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def admin_user():
    return AuthenticatedUserFactory(id=1, admin=True)


@pytest.fixture
def user_with_router_access():
    return AuthenticatedUserFactory(
        id=1,
        limits=[Limit(router_id=1, value=100, type=LimitType.RPM)],
        permissions=[],
    )


@pytest.fixture
def user_without_access():
    return AuthenticatedUserFactory(id=1, limits=[], permissions=[])


@pytest.fixture
def use_case(provider_client, provider_metrics_logger, router_repository, provider_repository):
    return GetHealthModelsUseCase(
        provider_client=provider_client,
        provider_metrics_logger=provider_metrics_logger,
        router_repository=router_repository,
        provider_repository=provider_repository,
    )


@pytest.fixture
def default_command(user_with_router_access):
    return GetHealthModelsCommand(authenticated_user=user_with_router_access)


def configure_metrics(
    provider_client,
    *,
    waiting: float = 0.0,
    running: float = 0.0,
    metrics_result: ProviderResponse | ProviderAdapterValidationResponseError | None = None,
):
    provider_client.forward.return_value = metrics_result or ProviderResponse(
        id="req-123", data=ProviderMetrics(waiting_requests=waiting, running_requests=running)
    )


def configure_models_fallback(provider_client, *, models_response):
    provider_client.forward.side_effect = [
        UnsupportedProviderEndpointError(endpoint=EndpointRoute.METRICS, provider_type=ProviderType.TEI),
        models_response,
    ]


class TestGetHealthModelsUseCase:
    @pytest.mark.asyncio
    async def test_should_return_all_models_when_user_is_admin(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        admin_user,
        default_command,
    ):
        # Arrange
        default_command.authenticated_user = admin_user
        router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="gpt-4", providers=1),
            RouterFactory(id=2, name="gpt-5", providers=1),
        ]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [
            provider,
            ProviderFactory(id=2, router_id=2, type=ProviderType.VLLM),
        ]
        configure_metrics(provider_client)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models == [
            ModelHealthStatus(id="gpt-4", status=HealthStatus.GREEN),
            ModelHealthStatus(id="gpt-5", status=HealthStatus.GREEN),
        ]

    @pytest.mark.asyncio
    async def test_should_return_empty_models_when_user_has_no_router_access(
        self, use_case, router_repository, provider_repository, user_without_access, default_command
    ):
        # Arrange
        default_command.authenticated_user = user_without_access
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)]

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models == []

    @pytest.mark.asyncio
    async def test_should_skip_routers_without_providers(self, use_case, router_repository, provider_repository, default_command):
        # Arrange
        router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="with-providers", providers=1),
            RouterFactory(id=2, name="no-providers", providers=0),
        ]
        provider_repository.get_all_providers.return_value = []

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert [model.id for model in result.models] == ["with-providers"]

    @pytest.mark.asyncio
    async def test_should_return_green_when_vllm_metrics_are_low(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client, waiting=0, running=0)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert len(result.models) == 1
        assert result.models[0].status == HealthStatus.GREEN
        provider_client.forward.assert_awaited_once()
        assert provider_client.forward.await_args.kwargs["request"].endpoint == EndpointRoute.METRICS
        assert provider_client.forward.await_args.kwargs["provider"] == provider

    @pytest.mark.asyncio
    async def test_should_return_yellow_when_vllm_has_waiting_requests(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client, waiting=1, running=0)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.YELLOW

    @pytest.mark.asyncio
    async def test_should_return_red_when_vllm_running_requests_exceed_threshold(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client, waiting=0, running=21)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_red_when_vllm_has_waiting_and_running_requests_exceed_threshold(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client, waiting=5, running=21)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_yellow_when_mistral_running_requests_exceed_yellow_threshold(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="mistral", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.MISTRAL)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client, waiting=0, running=59)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.YELLOW

    @pytest.mark.asyncio
    async def test_should_return_red_when_mistral_running_requests_exceed_red_threshold(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="mistral", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.MISTRAL)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client, waiting=0, running=64)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_red_when_metrics_request_fails(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_client)
        provider_client.forward.return_value = StatusCodeModelError(status_code=500, detail="error")

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_red_when_metrics_response_validation_fails(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(
            provider_client,
            metrics_result=ProviderAdapterValidationResponseError(provider_type=provider.type, errors=[{"msg": "invalid"}]),
        )

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_skip_metrics_check_when_models_fallback_succeeds(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.TEI)
        provider_repository.get_all_providers.return_value = [provider]
        configure_models_fallback(provider_client, models_response=ProviderResponse(id="req-123", data=Models(data=[])))

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.GREEN
        assert [call.kwargs["request"].endpoint for call in provider_client.forward.await_args_list] == [
            EndpointRoute.METRICS,
            EndpointRoute.MODELS,
        ]

    @pytest.mark.asyncio
    async def test_should_return_red_when_models_fallback_fails(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1, type=ProviderType.TEI)]
        configure_models_fallback(provider_client, models_response=StatusCodeModelError(status_code=500, detail="error"))

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_only_return_models_for_routers_the_user_can_access(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="accessible", providers=1),
            RouterFactory(id=2, name="forbidden", providers=1),
        ]
        accessible_provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [
            accessible_provider,
            ProviderFactory(id=2, router_id=2, type=ProviderType.VLLM),
        ]
        configure_metrics(provider_client)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert [model.id for model in result.models] == ["accessible"]

    @pytest.mark.asyncio
    async def test_should_not_query_providers_on_other_routers(
        self,
        use_case,
        router_repository,
        provider_repository,
        provider_client,
        default_command,
    ):
        # Arrange

        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        accessible_provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [
            accessible_provider,
            ProviderFactory(id=2, router_id=99, type=ProviderType.VLLM),
        ]
        configure_metrics(provider_client)

        # Act
        await use_case.execute(command=default_command)

        # Assert
        provider_client.forward.assert_awaited_once()
        assert provider_client.forward.await_args.kwargs["provider"] == accessible_provider
