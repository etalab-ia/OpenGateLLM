import datetime as dt
from unittest.mock import AsyncMock

import pytest

from api.domain.model.entities import HealthStatus
from api.domain.provider.entities import Metric
from api.domain.role.entities import Limit, LimitType
from api.domain.user.errors import UserExpiredError
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory, UserWithRoleFactory
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess

LATENCY_HISTORY_COUNT = 1800
UNIFORM_LATENCY_MS = 1000.0
HISTORICAL_LATENCIES_MS = [UNIFORM_LATENCY_MS] * LATENCY_HISTORY_COUNT


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
def use_case(provider_metrics_logger, router_repository, provider_repository, user_with_role_query):
    return GetHealthModelsUseCase(
        provider_metrics_logger=provider_metrics_logger,
        router_repository=router_repository,
        provider_repository=provider_repository,
        user_with_role_query=user_with_role_query,
    )


@pytest.fixture
def default_command():
    return GetHealthModelsCommand(user_id=1)


def configure_provider_metrics(provider_metrics_logger, *, inflight: int, history: list[float] | None = None):
    provider_metrics_logger.get_metric_history.return_value = history if history is not None else HISTORICAL_LATENCIES_MS
    provider_metrics_logger.get_current_inflight.return_value = inflight


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
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1)]

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
    async def test_should_return_green_status_when_inflight_is_low(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, provider_metrics_logger, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1)]
        configure_provider_metrics(provider_metrics_logger, inflight=0)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert len(result.models) == 1
        assert result.models[0].status == HealthStatus.GREEN
        provider_metrics_logger.get_metric_history.assert_called_once_with(
            provider_id=1,
            metric=Metric.LATENCY,
        )

    @pytest.mark.asyncio
    async def test_should_return_yellow_status_when_inflight_is_elevated(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, provider_metrics_logger, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1)]
        configure_provider_metrics(provider_metrics_logger, inflight=1)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.YELLOW

    @pytest.mark.asyncio
    async def test_should_return_red_status_when_inflight_is_high(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, provider_metrics_logger, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1)]
        configure_provider_metrics(provider_metrics_logger, inflight=2)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_keep_green_status_when_provider_has_no_metric_history(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, provider_metrics_logger, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [ProviderFactory(id=1, router_id=1)]
        provider_metrics_logger.get_metric_history.return_value = []

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.GREEN
        provider_metrics_logger.get_current_inflight.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_red_status_when_one_provider_is_overloaded(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, provider_metrics_logger, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=2)]
        provider_repository.get_all_providers.return_value = [
            ProviderFactory(id=1, router_id=1),
            ProviderFactory(id=2, router_id=1),
        ]
        provider_metrics_logger.get_metric_history.return_value = HISTORICAL_LATENCIES_MS
        provider_metrics_logger.get_current_inflight.side_effect = [0, 2]

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert result.models[0].status == HealthStatus.RED

    @pytest.mark.asyncio
    async def test_should_only_return_models_for_routers_the_user_can_access(
        self, use_case, user_with_role_query, router_repository, provider_repository, user_with_router_access, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_with_router_access
        router_repository.get_all_routers.return_value = [
            RouterFactory(id=1, name="accessible", providers=1),
            RouterFactory(id=2, name="forbidden", providers=1),
        ]
        provider_repository.get_all_providers.return_value = [
            ProviderFactory(id=1, router_id=1),
            ProviderFactory(id=2, router_id=2),
        ]

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, GetHealthModelsUseCaseSuccess)
        assert [model.id for model in result.models] == ["accessible"]

    @pytest.mark.asyncio
    async def test_should_not_query_metrics_for_providers_on_other_routers(
        self, use_case, user_with_role_query, router_repository, provider_repository, admin_user, provider_metrics_logger, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_all_routers.return_value = [RouterFactory(id=1, name="gpt-4", providers=1)]
        provider_repository.get_all_providers.return_value = [
            ProviderFactory(id=1, router_id=1),
            ProviderFactory(id=2, router_id=99),
        ]
        configure_provider_metrics(provider_metrics_logger, inflight=0)

        # Act
        await use_case.execute(command=default_command)

        # Assert
        provider_metrics_logger.get_metric_history.assert_called_once_with(
            provider_id=1,
            metric=Metric.LATENCY,
        )
        provider_metrics_logger.get_current_inflight.assert_called_once_with(provider_id=1)
