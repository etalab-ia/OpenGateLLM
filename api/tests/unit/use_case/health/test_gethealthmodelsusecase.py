import datetime as dt
from http import HTTPMethod
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.domain.model.entities import HealthStatus
from api.domain.model.errors import StatusCodeModelError
from api.domain.provider.entities import (
    Provider,
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderMetrics,
    ProviderOriginalResponse,
    ProviderType,
)
from api.domain.provider.errors import ProviderAdapterValidationResponseError, UnsupportedProviderEndpointError
from api.domain.role.entities import Limit, LimitType
from api.domain.user.errors import UserExpiredError
from api.infrastructure.http.adapters.metrics.mistral import MistralMetricsAdapter
from api.infrastructure.http.adapters.metrics.vllm import VllmMetricsAdapter
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory, UserWithRoleFactory
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess
from api.utils.variables import EndpointRoute

METRICS_TEXT = 'vllm:num_requests_running{model_name="my-model"} 0\nvllm:num_requests_waiting{model_name="my-model"} 0\n'


@pytest.fixture
def provider_adapter_builder():
    return MagicMock()


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
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def user_with_router_access():
    return UserWithRoleFactory(
        id=1,
        limits=[Limit(router_id=1, value=100, type=LimitType.RPM)],
        permissions=[],
    )


@pytest.fixture
def user_without_access():
    return UserWithRoleFactory(id=1, limits=[], permissions=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def use_case(provider_adapter_builder, provider_client, provider_metrics_logger, router_repository, provider_repository, user_with_role_query):
    return GetHealthModelsUseCase(
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_metrics_logger=provider_metrics_logger,
        router_repository=router_repository,
        provider_repository=provider_repository,
        user_with_role_query=user_with_role_query,
    )


@pytest.fixture
def default_command():
    return GetHealthModelsCommand(user_id=1)


def configure_metrics(
    provider_adapter_builder,
    provider_client,
    provider: Provider,
    *,
    waiting: float = 0.0,
    running: float = 0.0,
    format_response_result: ProviderFormattedResponse | ProviderAdapterValidationResponseError | None = None,
):
    adapter = MistralMetricsAdapter(provider=provider) if provider.type == ProviderType.MISTRAL else VllmMetricsAdapter(provider=provider)
    adapter.format_response = MagicMock(
        return_value=format_response_result or ProviderFormattedResponse(data=ProviderMetrics(waiting_requests=waiting, running_requests=running))
    )
    provider_adapter_builder.build.return_value = adapter
    provider_client.forward_request.return_value = ProviderOriginalResponse(text=METRICS_TEXT)


def configure_models_fallback(provider_adapter_builder, provider_client, *, models_response):
    models_adapter = MagicMock()
    models_adapter.format_request.return_value = ProviderFormattedRequest(method=HTTPMethod.GET, url="https://provider.test/v1/models")

    def build_side_effect(endpoint, provider):
        if endpoint == EndpointRoute.METRICS:
            return UnsupportedProviderEndpointError(endpoint=endpoint, provider_type=provider.type)
        return models_adapter

    provider_adapter_builder.build.side_effect = build_side_effect
    provider_client.forward_request.return_value = models_response


class TestGetHealthModelsUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(
        self, use_case, user_with_role_query, expired_user, default_command, router_repository, provider_repository
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
        router_repository.get_all_routers.assert_not_called()
        provider_repository.get_all_providers.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_models_when_user_has_no_router_access(
        self, use_case, user_with_role_query, router_repository, provider_repository, user_without_access, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_without_access
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)]

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models == []
        user_with_role_query.get_user_with_role_by_id.assert_called_once_with(user_id=1)

    @pytest.mark.asyncio
    async def test_should_skip_routers_without_providers(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="no-providers", providers=0),
            RouterFactory(id=2, name="with-providers", providers=1),
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
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider, waiting=0, running=0)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert len(result.models) == 1
        assert result.models[0].status == HealthStatus.GREEN
        provider_adapter_builder.build.assert_called_once_with(endpoint=EndpointRoute.METRICS, provider=provider)
        provider_client.forward_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_yellow_when_vllm_has_waiting_requests(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider, waiting=1, running=0)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.YELLOW

    @pytest.mark.asyncio
    async def test_should_return_red_when_vllm_running_requests_exceed_threshold(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider, waiting=0, running=21)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_red_when_vllm_has_waiting_and_running_requests_exceed_threshold(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider, waiting=5, running=21)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_yellow_when_mistral_running_requests_exceed_yellow_threshold(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="mistral", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.MISTRAL)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider, waiting=0, running=59)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.YELLOW

    @pytest.mark.asyncio
    async def test_should_return_red_when_mistral_running_requests_exceed_red_threshold(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="mistral", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.MISTRAL)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider, waiting=0, running=64)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_red_when_metrics_request_fails(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(provider_adapter_builder, provider_client, provider)
        provider_client.forward_request.return_value = StatusCodeModelError(status_code=500, detail="error")

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_return_red_when_metrics_response_validation_fails(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [provider]
        configure_metrics(
            provider_adapter_builder,
            provider_client,
            provider,
            format_response_result=ProviderAdapterValidationResponseError(provider_type=provider.type, errors=[{"msg": "invalid"}]),
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
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider = ProviderFactory(id=1, router_id=1, type=ProviderType.TEI)
        provider_repository.get_all_providers.return_value = [provider]
        configure_models_fallback(
            provider_adapter_builder,
            provider_client,
            models_response=ProviderOriginalResponse(data={"data": []}),
        )

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.GREEN
        assert provider_adapter_builder.build.call_count == 2
        provider_client.forward_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_red_when_models_fallback_fails(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1, type=ProviderType.TEI)]
        configure_models_fallback(
            provider_adapter_builder,
            provider_client,
            models_response=StatusCodeModelError(status_code=500, detail="error"),
        )

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_only_return_models_for_routers_the_user_can_access(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        provider_adapter_builder,
        provider_client,
        user_with_router_access,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_with_router_access
        router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="accessible", providers=1),
            RouterFactory(id=2, name="forbidden", providers=1),
        ]
        accessible_provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [
            accessible_provider,
            ProviderFactory(id=2, router_id=2, type=ProviderType.VLLM),
        ]
        configure_metrics(provider_adapter_builder, provider_client, accessible_provider)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert [model.id for model in result.models] == ["accessible"]

    @pytest.mark.asyncio
    async def test_should_not_query_providers_on_other_routers(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        admin_user,
        provider_adapter_builder,
        provider_client,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        accessible_provider = ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM)
        provider_repository.get_all_providers.return_value = [
            accessible_provider,
            ProviderFactory(id=2, router_id=99, type=ProviderType.VLLM),
        ]
        configure_metrics(provider_adapter_builder, provider_client, accessible_provider)

        # Act
        await use_case.execute(command=default_command)

        # Assert
        provider_adapter_builder.build.assert_called_once_with(endpoint=EndpointRoute.METRICS, provider=accessible_provider)
        provider_client.forward_request.assert_called_once()
