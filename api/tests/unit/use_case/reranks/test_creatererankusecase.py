from contextvars import ContextVar
import datetime as dt
from http import HTTPMethod
from unittest.mock import AsyncMock, MagicMock, call, create_autospec, patch

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import TooBusyModelError
from api.domain.provider.entities import (
    Metric,
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalResponse,
    ProviderType,
    ResponseMetrics,
)
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
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.domain.user.errors import UserHasNoAccessToRouterError
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.tests.integration.factories.vllm import VllmRerankResponseFactory
from api.tests.unit.use_case.factories import AutenticatedUserFactor, ProviderFactory, RouterFactory
from api.use_cases.reranks import CreateRerankCommand, CreateRerankUseCase, CreateRerankUseCaseSuccess


@pytest.fixture
def model_tokenizer():
    tokenizer = MagicMock()
    tokenizer.compute_tokens.return_value = 10
    return tokenizer


@pytest.fixture
def model_environmental_impacts_computer():
    computer = MagicMock()
    computer.compute.return_value = EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0)
    return computer


@pytest.fixture
def provider_adapter_builder():
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
def use_case(
    model_environmental_impacts_computer,
    model_tokenizer,
    provider_adapter_builder,
    provider_client,
    provider_load_balancer,
    provider_metrics_logger,
    provider_repository,
    router_rate_limiter,
    router_repository,
    rerank_router,
    rerank_provider,
    sample_rerank,
) -> CreateRerankUseCase:
    router_repository.get_router_by_name_or_alias.return_value = rerank_router
    provider_repository.get_all_providers_of_router.return_value = [rerank_provider]
    provider_load_balancer.find_best_provider.return_value = rerank_provider
    provider_metrics_logger.increment_inflight.return_value = True
    provider_client.forward_request.return_value = ProviderOriginalResponse(data=VllmRerankResponseFactory())
    rate_limit_state = rate_limit_state_factory()
    rate_limit_state.rpm = RpmRateLimitState(value=100, remaining=99, reset=int(dt.datetime.now(dt.UTC).timestamp()) + 30)
    router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state
    model_tokenizer.compute_tokens.return_value = 15
    mock_adapter = _mock_adapter(formatted_response=sample_rerank)
    provider_adapter_builder.build.return_value = mock_adapter

    return CreateRerankUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_load_balancer=provider_load_balancer,
        provider_metrics_logger=provider_metrics_logger,
        provider_repository=provider_repository,
        router_rate_limiter=router_rate_limiter,
        router_repository=router_repository,
    )


@pytest.fixture
def admin_user():
    return AutenticatedUserFactor(id=1, admin=True)


@pytest.fixture
def user_with_router_access():
    return AutenticatedUserFactor(id=1, without_permission=True, limits=[Limit(router_id=1, type=LimitType.RPM, value=100)])


@pytest.fixture
def request_context() -> ContextVar:
    return ContextVar("request_context")


@pytest.fixture
def make_command(request_context):
    def _make(user) -> CreateRerankCommand:
        request_context.set(RequestContext(user=user))
        return CreateRerankCommand(
            query="query",
            documents=["doc a", "doc b"],
            model="rerank-router",
            top_n=2,
            request_context=request_context,
        )

    return _make


@pytest.fixture
def default_command(make_command, admin_user):
    return make_command(admin_user)


@pytest.fixture
def user_without_router_access():
    return AutenticatedUserFactor(id=1, without_permission=True, limits=[])


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
def sample_rerank():
    return Rerank(
        id="rerank-1",
        model="rerank-router",
        results=[RerankResult(relevance_score=0.9, index=0)],
    )


@pytest.fixture
def mock_rerank_latency_120ms():
    with patch(
        "api.use_cases.reranks._creatererankusecase.time.perf_counter",
        side_effect=[0, 0.12],
    ):
        yield


@pytest.fixture
def mock_usage_cost():
    with patch(
        "api.domain.usage.entities.Usage.compute_request_cost",
        return_value=0.03,
    ):
        yield


@pytest.fixture
def mock_successful_rerank_flow(mock_rerank_latency_120ms, mock_usage_cost):
    yield


def rate_limit_state_factory(tpm_exceeded: bool = False, tpd_exceeded: bool = False, rpm_exceeded: bool = False, rpd_exceeded: bool = False):
    reset_time = int(dt.datetime.now(dt.UTC).timestamp()) + 30
    limit_state = RouterRateLimitState.admin_rate_limit_state()
    if tpm_exceeded:
        limit_state.tpm = TpmRateLimitState(value=10, remaining=0, reset=reset_time)
    if tpd_exceeded:
        limit_state.tpd = TpdRateLimitState(value=10, remaining=0, reset=reset_time)
    if rpm_exceeded:
        limit_state.rpm = RpmRateLimitState(value=10, remaining=0, reset=reset_time)
    if rpd_exceeded:
        limit_state.rpd = RpdRateLimitState(value=10, remaining=0, reset=reset_time)
    return limit_state


def assert_request_context(
    ctx,
    user_email: str | None = None,
    request_id: str | None = None,
    router_id: int | None = None,
    router_name: str | None = None,
    provider_id: int | None = None,
    provider_model_name: str | None = None,
    prompt_tokens: int | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
    kwh: float | None = None,
    kgco2eq: float | None = None,
):
    assert ctx.user is not None
    assert ctx.user.email == user_email
    assert ctx.id == request_id
    assert ctx.router_id == router_id
    assert ctx.router_name == router_name
    assert ctx.provider_id == provider_id
    assert ctx.provider_model_name == provider_model_name
    assert ctx.prompt_tokens == prompt_tokens
    assert ctx.total_tokens == total_tokens
    assert ctx.cost == cost
    assert ctx.kwh == kwh
    assert ctx.kgco2eq == kgco2eq


def _mock_adapter(*, formatted_request=None, formatted_response=None, request_error=None, response_error=None):
    adapter = create_autospec(
        HttpProviderAdapter, instance=True, spec_set=True
    )  # Autospec mock: unexpected kwargs / wrong signature should fail tests.
    adapter.format_request.return_value = formatted_request or ProviderFormattedRequest(
        method=HTTPMethod.POST,
        url="https://provider.example/rerank",
        body={},
    )
    adapter.format_response.return_value = response_error or ProviderFormattedResponse(data=formatted_response, metrics=ResponseMetrics(latency=120))
    if request_error is not None:
        adapter.format_request.return_value = request_error
    return adapter


class TestCreateRerankUseCase:
    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, default_command, admin_user):
        # Arrange
        use_case.router_repository.get_router_by_name_or_alias.return_value = RouterNotFoundError(name="rerank-router")

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterNotFoundError)

        ctx = default_command.request_context.get()
        assert_request_context(ctx, user_email=admin_user.email)

    @pytest.mark.asyncio
    async def test_should_return_router_has_no_providers_error_when_router_has_no_providers(self, use_case, default_command, admin_user):
        # Arrange
        rerank_router = RouterFactory(id=1, name="rerank-router", type=RouterType.TEXT_CLASSIFICATION, providers=0)
        use_case.router_repository.get_router_by_name_or_alias.return_value = rerank_router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterHasNoProvidersError)
        assert result.id == 1

        ctx = default_command.request_context.get()
        assert_request_context(ctx, user_email=admin_user.email, router_id=rerank_router.id, router_name=rerank_router.name)

    @pytest.mark.asyncio
    async def test_should_return_router_has_wrong_type_error_when_router_is_not_text_classification(self, use_case, default_command, admin_user):
        # Arrange
        rerank_router = RouterFactory(id=1, name="rerank-router", type=RouterType.TEXT_GENERATION, providers=1)
        use_case.router_repository.get_router_by_name_or_alias.return_value = rerank_router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterHasWrongTypeError)
        assert result.actual_type == RouterType.TEXT_GENERATION
        assert result.expected_type == RouterType.TEXT_CLASSIFICATION

        ctx = default_command.request_context.get()
        assert_request_context(ctx, user_email=admin_user.email, router_id=rerank_router.id, router_name=rerank_router.name)

    @pytest.mark.asyncio
    async def test_should_return_user_has_no_access_error_when_user_cannot_access_router(
        self, use_case, user_without_router_access, rerank_router, make_command
    ):
        # Arrange
        command = make_command(user_without_router_access)
        use_case.router_repository.get_router_by_name_or_alias.return_value = rerank_router

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UserHasNoAccessToRouterError)
        assert result.id == rerank_router.id

        ctx = command.request_context.get()
        assert_request_context(ctx, user_email=user_without_router_access.email, router_id=rerank_router.id, router_name=rerank_router.name)

    @pytest.mark.asyncio
    async def test_should_call_model_tokenizer_with_request_prompts_before_rate_limit_check(
        self, use_case, user_with_router_access, model_tokenizer, make_command
    ):
        # Arrange
        command = make_command(user_with_router_access)
        use_case.router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state_factory(tpm_exceeded=True)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, RouterRateLimitExceededError)
        model_tokenizer.compute_tokens.assert_called_once_with(texts=["query", "doc a", "doc b"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "limit_type,rate_limit_state",
        [
            (LimitType.RPM, rate_limit_state_factory(rpm_exceeded=True)),
            (LimitType.RPD, rate_limit_state_factory(rpd_exceeded=True)),
            (LimitType.TPM, rate_limit_state_factory(tpm_exceeded=True)),
            (LimitType.TPD, rate_limit_state_factory(tpd_exceeded=True)),
            (LimitType.TPM, rate_limit_state_factory(tpm_exceeded=True, tpd_exceeded=True, rpm_exceeded=True, rpd_exceeded=True)),
        ],
    )
    async def test_should_return_router_rate_limit_exceeded_error_when_one_limit_is_exceeded(
        self,
        use_case,
        user_with_router_access,
        provider_load_balancer,
        router_rate_limiter,
        rerank_router,
        rerank_provider,
        make_command,
        limit_type,
        rate_limit_state,
    ):
        # Arrange
        command = make_command(user_with_router_access)
        use_case.router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, RouterRateLimitExceededError)
        assert result.id == rerank_router.id
        assert result.limit_type == limit_type
        assert result.headers == rate_limit_state.build_limit_headers
        router_rate_limiter.update_rate_limit_state.assert_not_called()
        provider_load_balancer.find_best_provider.assert_called_once()

        ctx = command.request_context.get()
        assert_request_context(
            ctx,
            user_email=user_with_router_access.email,
            router_id=rerank_router.id,
            router_name=rerank_router.name,
            provider_id=rerank_provider.id,
            provider_model_name=rerank_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_provider_adapter_validation_request_error_when_request_is_invalid(
        self, use_case, provider_adapter_builder, rerank_router, rerank_provider, default_command, admin_user
    ):
        # Arrange
        validation_error = ProviderAdapterValidationRequestError(provider_type=ProviderType.TEI, errors=[{"msg": "invalid"}])
        mock_adapter = _mock_adapter(request_error=validation_error)
        provider_adapter_builder.build.return_value = mock_adapter

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == validation_error

        ctx = default_command.request_context.get()
        assert_request_context(
            ctx,
            user_email=admin_user.email,
            router_id=rerank_router.id,
            router_name=rerank_router.name,
            provider_id=rerank_provider.id,
            provider_model_name=rerank_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_error_when_provider_forward_request_fails(
        self, use_case, provider_metrics_logger, provider_client, rerank_router, rerank_provider, default_command, admin_user
    ):
        # Arrange
        provider_error = TooBusyModelError(status_code=503, detail="busy")
        provider_client.forward_request.return_value = provider_error

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == provider_error
        provider_metrics_logger.decrement_inflight.assert_called_once_with(provider_id=rerank_provider.id)

        ctx = default_command.request_context.get()
        assert_request_context(
            ctx,
            user_email=admin_user.email,
            router_id=rerank_router.id,
            router_name=rerank_router.name,
            provider_id=rerank_provider.id,
            provider_model_name=rerank_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_provider_adapter_validation_response_error_when_response_is_invalid(
        self,
        use_case,
        provider_metrics_logger,
        provider_client,
        provider_adapter_builder,
        rerank_router,
        rerank_provider,
        default_command,
        admin_user,
    ):
        # Arrange
        provider_metrics_logger.increment_inflight.return_value = False
        provider_client.forward_request.return_value = ProviderOriginalResponse(data={}, metrics=ResponseMetrics(latency=80))
        validation_error = ProviderAdapterValidationResponseError(provider_type=ProviderType.TEI, errors=[{"msg": "invalid"}])
        mock_adapter = _mock_adapter(response_error=validation_error)
        provider_adapter_builder.build.return_value = mock_adapter

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == validation_error
        provider_metrics_logger.decrement_inflight.assert_not_called()

        ctx = default_command.request_context.get()
        assert_request_context(
            ctx,
            user_email=admin_user.email,
            router_id=rerank_router.id,
            router_name=rerank_router.name,
            provider_id=rerank_provider.id,
            provider_model_name=rerank_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_rerank_when_admin_user_and_flow_succeeds(
        self,
        use_case,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        rerank_router,
        rerank_provider,
        sample_rerank,
        router_rate_limiter,
        model_tokenizer,
        model_environmental_impacts_computer,
        default_command,
        admin_user,
        mock_successful_rerank_flow,
    ):
        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, CreateRerankUseCaseSuccess)
        assert result.data.id == sample_rerank.id
        assert result.data.results == sample_rerank.results
        assert result.data.model == sample_rerank.model
        assert result.data.usage == Usage(
            prompt_tokens=15,
            completion_tokens=0,
            total_tokens=15,
            cost=0.03,
            impacts=EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0),
        )
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
        model_tokenizer.compute_tokens.assert_called_once_with(texts=["query", "doc a", "doc b"])
        model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=rerank_provider.model_active_params,
            model_total_params=rerank_provider.model_total_params,
            model_zone=rerank_provider.model_hosting_zone,
            completion_tokens=0,
            request_latency=120,
        )

        assert result.headers == rate_limit_state_factory().build_limit_headers
        router_rate_limiter.get_rate_limit_state.assert_not_awaited()
        router_rate_limiter.update_rate_limit_state.assert_not_awaited()

        ctx = default_command.request_context.get()
        assert_request_context(
            ctx,
            user_email=admin_user.email,
            request_id=sample_rerank.id,
            router_id=rerank_router.id,
            router_name=rerank_router.name,
            provider_id=rerank_provider.id,
            provider_model_name=rerank_provider.model_name,
            prompt_tokens=15,
            total_tokens=15,
            cost=result.data.usage.cost,
        )

    @pytest.mark.asyncio
    async def test_should_enrich_when_non_admin_user_and_flow_succeeds(
        self,
        use_case,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        provider_adapter_builder,
        router_rate_limiter,
        model_tokenizer,
        model_environmental_impacts_computer,
        user_with_router_access,
        rerank_router,
        rerank_provider,
        sample_rerank,
        make_command,
        mock_successful_rerank_flow,
    ):
        # Arrange
        command = make_command(user_with_router_access)
        rate_limit_state = rate_limit_state_factory()
        rate_limit_state.rpm = RpmRateLimitState(
            value=100,
            remaining=99,
            reset=int(dt.datetime.now(dt.UTC).timestamp()) + 30,
        )
        router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state
        model_tokenizer.compute_tokens.return_value = 15
        mock_adapter = _mock_adapter(formatted_response=sample_rerank)
        provider_adapter_builder.build.return_value = mock_adapter

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateRerankUseCaseSuccess)
        assert result.data.id == sample_rerank.id
        assert result.data.results == sample_rerank.results
        assert result.data.model == sample_rerank.model
        assert result.data.usage == Usage(
            prompt_tokens=15,
            completion_tokens=0,
            total_tokens=15,
            cost=0.03,
            impacts=EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0),
        )
        assert result.headers == rate_limit_state.build_limit_headers
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
        model_tokenizer.compute_tokens.assert_called_once_with(texts=["query", "doc a", "doc b"])
        model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=rerank_provider.model_active_params,
            model_total_params=rerank_provider.model_total_params,
            model_zone=rerank_provider.model_hosting_zone,
            completion_tokens=0,
            request_latency=120,
        )

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

        ctx = command.request_context.get()
        assert_request_context(
            ctx,
            user_email=user_with_router_access.email,
            request_id=sample_rerank.id,
            router_id=rerank_router.id,
            router_name=rerank_router.name,
            provider_id=rerank_provider.id,
            provider_model_name=rerank_provider.model_name,
            prompt_tokens=15,
            total_tokens=15,
            cost=result.data.usage.cost,
        )
