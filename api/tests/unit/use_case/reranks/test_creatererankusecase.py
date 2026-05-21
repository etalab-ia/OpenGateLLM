from contextvars import ContextVar
import datetime as dt
from http import HTTPMethod
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import TooBusyModelError
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.rerank.entities import Rerank, RerankResult
from api.domain.role.entities import Limit, LimitType
from api.domain.router.entities import RouterRateLimitState, RpdRateLimitState, RpmRateLimitState, TpdRateLimitState, TpmRateLimitState
from api.domain.router.errors import (
    RouterHasNoProvidersError,
    RouterHasWrongTypeError,
    RouterNotFoundError,
    RouterRateLimitExceededError,
)
from api.domain.user.errors import UserExpiredError, UserHasNoAccessToRouterError
from api.infrastructure.fastapi.context import RequestContext
from api.schemas.admin.roles import LimitType as SchemaLimitType
from api.schemas.core.models import Metric
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory, UserWithRoleFactory
from api.use_cases.reranks import CreateRerankCommand, CreateRerankUseCase, CreateRerankUseCaseSuccess


@pytest.fixture
def model_environmental_impacts_computer():
    return MagicMock()


@pytest.fixture
def model_tokenizer():
    return MagicMock()


@pytest.fixture
def provider_client():
    return AsyncMock()


@pytest.fixture
def provider_load_balancer():
    return AsyncMock()


@pytest.fixture
def provider_metrics_logger():
    return AsyncMock()


@pytest.fixture
def provider_repository():
    return AsyncMock()


@pytest.fixture
def router_rate_limiter():
    return AsyncMock()


@pytest.fixture
def router_repository():
    return AsyncMock()


@pytest.fixture
def user_with_role_query():
    return AsyncMock()


@pytest.fixture
def use_case(
    model_environmental_impacts_computer,
    model_tokenizer,
    provider_client,
    provider_load_balancer,
    provider_metrics_logger,
    provider_repository,
    router_rate_limiter,
    router_repository,
    user_with_role_query,
) -> CreateRerankUseCase:
    return CreateRerankUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_client=provider_client,
        provider_load_balancer=provider_load_balancer,
        provider_metrics_logger=provider_metrics_logger,
        provider_repository=provider_repository,
        router_rate_limiter=router_rate_limiter,
        router_repository=router_repository,
        user_with_role_query=user_with_role_query,
    )


@pytest.fixture
def request_context() -> ContextVar:
    context = ContextVar("request_context")
    context.set(RequestContext(user_id=1))
    return context


@pytest.fixture
def admin_user():
    return UserWithRoleFactory(id=1, admin=True)


@pytest.fixture
def user_with_router_access():
    return UserWithRoleFactory(
        id=1,
        without_permission=True,
        limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
    )


@pytest.fixture
def user_without_router_access():
    return UserWithRoleFactory(id=1, without_permission=True, limits=[])


@pytest.fixture
def expired_user():
    return UserWithRoleFactory(id=1, expires=int((dt.datetime.now() - dt.timedelta(days=1)).timestamp()))


@pytest.fixture
def rerank_router():
    return RouterFactory(
        id=1,
        name="rerank-router",
        type=RouterType.TEXT_CLASSIFICATION,
        providers=1,
        load_balancing_strategy="shuffle",
    )


@pytest.fixture
def rerank_provider():
    return ProviderFactory(id=1, router_id=1, type=ProviderType.TEI, model_name="bge-reranker")


@pytest.fixture
def default_command(request_context):
    return CreateRerankCommand(
        query="query",
        documents=["doc a", "doc b"],
        model="rerank-router",
        top_n=2,
        request_context=request_context,
    )


@pytest.fixture
def sample_rerank():
    return Rerank(
        id="rerank-1",
        model="rerank-router",
        results=[RerankResult(relevance_score=0.9, index=0)],
    )


def _rate_limit_state(
    *,
    rpm_value: int | None = None,
    rpm_remaining: int = 0,
    rpm_reset: int = 0,
) -> RouterRateLimitState:
    return RouterRateLimitState(
        rpm=RpmRateLimitState(value=rpm_value, remaining=rpm_remaining, reset=rpm_reset),
        rpd=RpdRateLimitState(value=None),
        tpm=TpmRateLimitState(value=None),
        tpd=TpdRateLimitState(value=None),
    )


def _mock_adapter(*, prompt_tokens: int = 10, formatted_request=None, formatted_response=None, request_error=None, response_error=None):
    adapter = MagicMock()
    adapter.compute_prompt_tokens.return_value = prompt_tokens
    adapter.format_request.return_value = formatted_request or ProviderFormattedRequest(
        method=HTTPMethod.POST,
        url="https://provider.example/rerank",
        body={},
    )
    adapter.format_response.return_value = response_error or ProviderFormattedResponse(
        data=formatted_response,
        latency=120,
    )
    if request_error is not None:
        adapter.format_request.return_value = request_error
    return adapter


def configure_successful_execute(
    *,
    user_with_role_query,
    router_repository,
    provider_repository,
    provider_load_balancer,
    provider_metrics_logger,
    provider_client,
    router_rate_limiter,
    admin_user,
    rerank_router,
    rerank_provider,
    sample_rerank,
    prompt_tokens: int = 10,
):
    user_with_role_query.get_user_with_role_by_id.return_value = admin_user
    router_repository.get_router_by_name_or_alias.return_value = rerank_router
    provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
    provider_load_balancer.find_best_provider.return_value = rerank_provider
    provider_metrics_logger.increment_inflight.return_value = True
    provider_client.forward_request.return_value = ProviderOriginalResponse(data={}, latency=120)
    router_rate_limiter.get_rate_limit_state.return_value = _rate_limit_state(
        rpm_value=100,
        rpm_remaining=100,
        rpm_reset=int(dt.datetime.now(dt.UTC).timestamp()) + 60,
    )
    return _mock_adapter(prompt_tokens=prompt_tokens, formatted_response=sample_rerank)


class TestCreateRerankUseCase:
    @pytest.mark.asyncio
    async def test_should_return_user_expired_error_when_user_expired(
        self,
        use_case,
        user_with_role_query,
        expired_user,
        default_command,
        router_repository,
        provider_repository,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = expired_user

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserExpiredError)
        router_repository.get_router_by_name_or_alias.assert_not_called()
        provider_repository.get_all_providers_of_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(
        self,
        use_case,
        user_with_role_query,
        admin_user,
        router_repository,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_name_or_alias.return_value = RouterNotFoundError(name="rerank-router")

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterNotFoundError)

    @pytest.mark.asyncio
    async def test_should_return_router_has_no_providers_error_when_router_has_no_providers(
        self,
        use_case,
        user_with_role_query,
        admin_user,
        router_repository,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_name_or_alias.return_value = RouterFactory(
            id=1,
            name="rerank-router",
            type=RouterType.TEXT_CLASSIFICATION,
            providers=0,
        )

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterHasNoProvidersError)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_should_return_router_has_wrong_type_error_when_router_is_not_text_classification(
        self, use_case, user_with_role_query, admin_user, router_repository, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_name_or_alias.return_value = RouterFactory(
            id=1,
            name="rerank-router",
            type=RouterType.TEXT_GENERATION,
            providers=1,
        )

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterHasWrongTypeError)
        assert result.actual_type == RouterType.TEXT_GENERATION
        assert result.expected_type == RouterType.TEXT_CLASSIFICATION

    @pytest.mark.asyncio
    async def test_should_return_user_has_no_access_error_when_user_cannot_access_router(
        self, use_case, user_with_role_query, user_without_router_access, router_repository, rerank_router, default_command
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_without_router_access
        router_repository.get_router_by_name_or_alias.return_value = rerank_router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, UserHasNoAccessToRouterError)
        assert result.id == rerank_router.id

    @pytest.mark.asyncio
    async def test_should_return_router_rate_limit_exceeded_error_when_limits_are_exceeded(
        self,
        use_case,
        user_with_role_query,
        user_with_router_access,
        router_repository,
        provider_repository,
        provider_load_balancer,
        router_rate_limiter,
        rerank_router,
        rerank_provider,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_with_router_access
        router_repository.get_router_by_name_or_alias.return_value = rerank_router
        provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
        provider_load_balancer.find_best_provider.return_value = rerank_provider
        rate_limit_state = _rate_limit_state(
            rpm_value=10,
            rpm_remaining=0,
            rpm_reset=int(dt.datetime.now(dt.UTC).timestamp()) + 30,
        )
        router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state
        mock_adapter = _mock_adapter()

        # Act
        with patch("api.use_cases.reranks._creatererankusecase.build_adapter", return_value=mock_adapter):
            result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterRateLimitExceededError)
        assert result.id == rerank_router.id
        assert result.limit_type == SchemaLimitType.RPM
        assert result.headers == rate_limit_state.build_limit_headers
        router_rate_limiter.update_rate_limit_state.assert_not_called()
        provider_load_balancer.find_best_provider.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_provider_adapter_validation_request_error_when_request_is_invalid(
        self,
        use_case,
        user_with_role_query,
        admin_user,
        router_repository,
        provider_repository,
        provider_load_balancer,
        rerank_router,
        rerank_provider,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_name_or_alias.return_value = rerank_router
        provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
        provider_load_balancer.find_best_provider.return_value = rerank_provider
        validation_error = ProviderAdapterValidationRequestError(provider_type=ProviderType.TEI, errors=[{"msg": "invalid"}])
        mock_adapter = _mock_adapter(request_error=validation_error)

        # Act
        with patch("api.use_cases.reranks._creatererankusecase.build_adapter", return_value=mock_adapter):
            result = await use_case.execute(command=default_command)

        # Assert
        assert result == validation_error

    @pytest.mark.asyncio
    async def test_should_return_error_when_provider_forward_request_fails(
        self,
        use_case,
        user_with_role_query,
        admin_user,
        router_repository,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        provider_client,
        rerank_router,
        rerank_provider,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_name_or_alias.return_value = rerank_router
        provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
        provider_load_balancer.find_best_provider.return_value = rerank_provider
        provider_metrics_logger.increment_inflight.return_value = True
        provider_error = TooBusyModelError(status_code=503, detail="busy")
        provider_client.forward_request.return_value = provider_error
        mock_adapter = _mock_adapter()

        # Act
        with patch("api.use_cases.reranks._creatererankusecase.build_adapter", return_value=mock_adapter):
            result = await use_case.execute(command=default_command)

        # Assert
        assert result == provider_error
        provider_metrics_logger.decrement_inflight.assert_called_once_with(provider_id=rerank_provider.id)

    @pytest.mark.asyncio
    async def test_should_return_provider_adapter_validation_response_error_when_response_is_invalid(
        self,
        use_case,
        user_with_role_query,
        admin_user,
        router_repository,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        provider_client,
        rerank_router,
        rerank_provider,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = admin_user
        router_repository.get_router_by_name_or_alias.return_value = rerank_router
        provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
        provider_load_balancer.find_best_provider.return_value = rerank_provider
        provider_metrics_logger.increment_inflight.return_value = False
        provider_client.forward_request.return_value = ProviderOriginalResponse(data={}, latency=80)
        validation_error = ProviderAdapterValidationResponseError(provider_type=ProviderType.TEI, errors=[{"msg": "invalid"}])
        mock_adapter = _mock_adapter(response_error=validation_error)

        # Act
        with patch("api.use_cases.reranks._creatererankusecase.build_adapter", return_value=mock_adapter):
            result = await use_case.execute(command=default_command)

        # Assert
        assert result == validation_error
        provider_metrics_logger.decrement_inflight.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_rerank_when_admin_user_and_flow_succeeds(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        provider_client,
        admin_user,
        rerank_router,
        rerank_provider,
        sample_rerank,
        default_command,
    ):
        # Arrange
        mock_adapter = configure_successful_execute(
            user_with_role_query=user_with_role_query,
            router_repository=router_repository,
            provider_repository=provider_repository,
            provider_load_balancer=provider_load_balancer,
            provider_metrics_logger=provider_metrics_logger,
            provider_client=provider_client,
            router_rate_limiter=AsyncMock(),
            admin_user=admin_user,
            rerank_router=rerank_router,
            rerank_provider=rerank_provider,
            sample_rerank=sample_rerank,
        )

        # Act
        with patch("api.use_cases.reranks._creatererankusecase.build_adapter", return_value=mock_adapter):
            result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, CreateRerankUseCaseSuccess)
        assert result.data == sample_rerank
        assert result.headers == RouterRateLimitState.admin_rate_limit_state().build_limit_headers
        provider_repository.get_all_providers_of_router.assert_awaited_once_with(router_id=rerank_router.id)
        provider_load_balancer.find_best_provider.assert_awaited_once_with(
            strategy=rerank_router.load_balancing_strategy,
            providers=[rerank_provider],
        )
        provider_metrics_logger.log_metric.assert_has_awaits(
            [
                call(provider_id=rerank_provider.id, metric=Metric.LATENCY, value=120),
                call(provider_id=rerank_provider.id, metric=Metric.NORMALIZED_LATENCY, value=120),
            ]
        )
        provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=rerank_provider.id)

    @pytest.mark.asyncio
    async def test_should_update_rate_limits_for_non_admin_user_with_router_access(
        self,
        use_case,
        user_with_role_query,
        router_repository,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        provider_client,
        router_rate_limiter,
        user_with_router_access,
        rerank_router,
        rerank_provider,
        sample_rerank,
        default_command,
    ):
        # Arrange
        user_with_role_query.get_user_with_role_by_id.return_value = user_with_router_access
        router_repository.get_router_by_name_or_alias.return_value = rerank_router
        provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
        provider_load_balancer.find_best_provider.return_value = rerank_provider
        provider_metrics_logger.increment_inflight.return_value = True
        provider_client.forward_request.return_value = ProviderOriginalResponse(data={}, latency=50)
        rate_limit_state = _rate_limit_state(
            rpm_value=100,
            rpm_remaining=99,
            rpm_reset=int(dt.datetime.now(dt.UTC).timestamp()) + 45,
        )
        router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state
        mock_adapter = _mock_adapter(prompt_tokens=15, formatted_response=sample_rerank)

        # Act
        with patch("api.use_cases.reranks._creatererankusecase.build_adapter", return_value=mock_adapter):
            result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, CreateRerankUseCaseSuccess)
        assert result.data == sample_rerank
        assert result.headers == rate_limit_state.build_limit_headers
        router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=rerank_router.id,
            prompt_tokens=15,
        )
        router_rate_limiter.update_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=rerank_router.id,
            prompt_tokens=15,
        )
