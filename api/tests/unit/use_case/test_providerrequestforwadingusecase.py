from http import HTTPMethod
from unittest.mock import AsyncMock, create_autospec, patch

import pytest

from api.domain import ForwardablePayload
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.model.entities import ModelJsonResponse
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import TooBusyModelError
from api.domain.provider import (
    ProviderAdapter,
    ProviderAdapterBuilder,
    ProviderClient,
    ProviderLoadBalancer,
    ProviderMetricsLogger,
    ProviderRepository,
)
from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalResponse,
    ProviderType,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.role.entities import Limit, LimitType
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterRateLimitState, RpmRateLimitState, TpmRateLimitState
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.usage import UsageRecorder
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.schemas.core.models import Metric
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases._providerrequestforwardingusecase import (
    ForwardingCommand,
    ProviderRequestForwardingUseCase,
    ProviderRequestForwardingUseCaseSuccess,
)
from api.utils.variables import EndpointRoute


class ForwardingTestPayload(ForwardablePayload):
    model: str | None = "test-router"

    def get_prompts(self) -> list[str]:
        return ["hello"]


class ForwardingTestData(ModelJsonResponse):
    id: str = "req-1"
    usage: Usage | None = None

    def get_completions(self) -> list[str]:
        return ["world"]


class ForwardingTestCommand(ForwardingCommand[ForwardingTestPayload]): ...


class ForwardingTestUseCase(ProviderRequestForwardingUseCase[ForwardingTestCommand, ForwardingTestData]):
    ROUTER_TYPE = RouterType.TEXT_GENERATION
    ENDPOINT = EndpointRoute.CHAT_COMPLETIONS


@pytest.fixture
def model_tokenizer():
    tokenizer = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    return tokenizer


@pytest.fixture
def model_environmental_impacts_computer():
    computer = create_autospec(ModelEnvironmentalImpactsComputer, instance=True, spec_set=True)
    computer.compute.return_value = EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0)
    return computer


@pytest.fixture
def provider_adapter_builder():
    return create_autospec(ProviderAdapterBuilder, instance=True, spec_set=True)


@pytest.fixture
def provider_client():
    return create_autospec(ProviderClient, instance=True, spec_set=True)


@pytest.fixture
def provider_load_balancer():
    return create_autospec(ProviderLoadBalancer, instance=True, spec_set=True)


@pytest.fixture
def provider_metrics_logger():
    return create_autospec(ProviderMetricsLogger, instance=True, spec_set=True)


@pytest.fixture
def provider_repository():
    return create_autospec(ProviderRepository, instance=True, spec_set=True)


@pytest.fixture
def router_rate_limiter():
    return create_autospec(RouterRateLimiter, instance=True, spec_set=True)


@pytest.fixture
def router_repository():
    return create_autospec(RouterRepository, instance=True, spec_set=True)


@pytest.fixture
def usage_recorder():
    return create_autospec(UsageRecorder, instance=True, spec_set=True)


@pytest.fixture
def router():
    return RouterFactory(
        id=1,
        name="test-router",
        type=RouterType.TEXT_GENERATION,
        providers=1,
        load_balancing_strategy="shuffle",
        cost_prompt_tokens=0.001,
        cost_completion_tokens=0.002,
    )


@pytest.fixture
def provider():
    return ProviderFactory(id=1, router_id=1, type=ProviderType.VLLM, model_name="vllm-model")


@pytest.fixture
def sample_data():
    return ForwardingTestData()


@pytest.fixture
def payload():
    return ForwardingTestPayload()


@pytest.fixture
def admin_user():
    return AuthenticatedUserFactory(id=1, admin=True)


@pytest.fixture
def user_with_router_access():
    return AuthenticatedUserFactory(
        id=1,
        without_permission=True,
        limits=[
            Limit(router_id=1, type=LimitType.RPM, value=100),
            Limit(router_id=999, type=LimitType.TPM, value=50),
        ],
    )


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
    usage_recorder,
) -> ForwardingTestUseCase:
    return ForwardingTestUseCase(
        model_environmental_impacts_computer=model_environmental_impacts_computer,
        model_tokenizer=model_tokenizer,
        provider_adapter_builder=provider_adapter_builder,
        provider_client=provider_client,
        provider_load_balancer=provider_load_balancer,
        provider_metrics_logger=provider_metrics_logger,
        provider_repository=provider_repository,
        router_rate_limiter=router_rate_limiter,
        router_repository=router_repository,
        usage_recorder=usage_recorder,
    )


def _mock_adapter(*, formatted_response=None, formatted_text=None, request_error=None, response_error=None):
    adapter = create_autospec(ProviderAdapter, instance=True, spec_set=True)
    adapter.format_request.return_value = ProviderFormattedRequest(
        method=HTTPMethod.POST,
        url="https://provider.example/v1/chat/completions",
        body={},
    )
    if response_error is not None:
        adapter.format_response.return_value = response_error
    elif formatted_text is not None:
        adapter.format_response.return_value = ProviderFormattedResponse(id="req-1", text=formatted_text)
    elif formatted_response is not None:
        adapter.format_response.return_value = ProviderFormattedResponse(id=formatted_response.id, data=formatted_response)
    if request_error is not None:
        adapter.format_request.return_value = request_error
    return adapter


class TestResolveRouter:
    @pytest.mark.asyncio
    async def test_should_return_repository_error_when_router_does_not_exist(self, use_case, admin_user):
        # Arrange
        use_case.router_repository.get_router_by_name_or_alias.return_value = RouterNotFoundError(name="test-router")

        # Act
        result = await use_case._resolve_router(authenticated_user=admin_user, model_name_or_alias="test-router")

        # Assert
        assert isinstance(result, RouterNotFoundError)
        use_case.router_repository.get_router_by_name_or_alias.assert_awaited_once_with(name_or_alias="test-router")
        use_case.usage_recorder.record_router.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_router_has_no_providers_error_when_router_has_no_providers(self, use_case, admin_user):
        # Arrange
        router = RouterFactory(id=1, name="test-router", type=RouterType.TEXT_GENERATION, providers=0)
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=admin_user, model_name_or_alias="test-router")

        # Assert
        assert isinstance(result, RouterHasNoProvidersError)
        assert result.id == 1
        use_case.usage_recorder.record_router.assert_called_once_with(router_id=router.id, router_name=router.name)

    @pytest.mark.asyncio
    async def test_should_return_router_has_wrong_type_error_when_router_type_does_not_match(self, use_case, admin_user):
        # Arrange
        router = RouterFactory(id=1, name="test-router", type=RouterType.TEXT_EMBEDDINGS_INFERENCE, providers=1)
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=admin_user, model_name_or_alias="test-router")

        # Assert
        assert isinstance(result, RouterHasWrongTypeError)
        assert result.actual_type == RouterType.TEXT_EMBEDDINGS_INFERENCE
        assert result.expected_type == RouterType.TEXT_GENERATION

    @pytest.mark.asyncio
    async def test_should_return_user_has_no_access_error_when_user_cannot_access_router(self, use_case, router):
        # Arrange
        user = AuthenticatedUserFactory(id=1, without_permission=True, limits=[])
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=user, model_name_or_alias="test-router")

        # Assert
        assert isinstance(result, UserHasNoAccessToRouterError)
        assert result.id == router.id

    @pytest.mark.asyncio
    async def test_should_return_insufficient_budget_error_when_router_is_billable_and_user_budget_is_zero(
        self, use_case, router, user_with_router_access
    ):
        # Arrange
        user = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            budget=0,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=user, model_name_or_alias="test-router")

        # Assert
        assert isinstance(result, UserHasInsufficientBudgetError)

    @pytest.mark.asyncio
    async def test_should_return_insufficient_budget_error_when_router_bills_completion_only_and_user_budget_is_zero(
        self, use_case, user_with_router_access
    ):
        # Arrange
        user = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            budget=0,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        router = RouterFactory(
            id=1,
            name="test-router",
            type=RouterType.TEXT_GENERATION,
            providers=1,
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.002,
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=user, model_name_or_alias="test-router")

        # Assert
        assert isinstance(result, UserHasInsufficientBudgetError)

    @pytest.mark.asyncio
    async def test_should_return_router_when_not_billable_even_if_user_budget_is_zero(self, use_case, user_with_router_access):
        # Arrange
        user = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            budget=0,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        router = RouterFactory(
            id=1,
            name="test-router",
            type=RouterType.TEXT_GENERATION,
            providers=1,
            free=True,
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=user, model_name_or_alias="test-router")

        # Assert
        assert result is router

    @pytest.mark.asyncio
    async def test_should_return_router_when_checks_pass(self, use_case, admin_user, router):
        # Arrange
        use_case.router_repository.get_router_by_name_or_alias.return_value = router

        # Act
        result = await use_case._resolve_router(authenticated_user=admin_user, model_name_or_alias="test-router")

        # Assert
        assert result is router
        use_case.usage_recorder.record_router.assert_called_once_with(router_id=router.id, router_name=router.name)


class TestCheckRateLimits:
    @pytest.mark.asyncio
    async def test_should_return_admin_rate_limit_state_without_calling_limiter_when_user_is_admin(self, use_case, admin_user, router):
        # Act
        result = await use_case._check_rate_limits(authenticated_user=admin_user, router=router, prompt_tokens=1)

        # Assert
        assert result == RouterRateLimitState.admin_rate_limit_state()
        use_case.router_rate_limiter.get_rate_limit_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_rate_limit_exceeded_error_when_a_limit_is_exceeded(self, use_case, user_with_router_access, router):
        # Arrange
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        rate_limit_state.rpm = RpmRateLimitState(value=10, remaining=0, reset=0)
        use_case.router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state

        # Act
        result = await use_case._check_rate_limits(authenticated_user=user_with_router_access, router=router, prompt_tokens=1)

        # Assert
        assert isinstance(result, RouterRateLimitExceededError)
        assert result.id == router.id
        assert result.limit_type == LimitType.RPM
        assert result.headers == rate_limit_state.build_limit_headers
        use_case.router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=router.id,
        )

    @pytest.mark.asyncio
    async def test_should_return_rate_limit_exceeded_error_without_updating_state_when_prompt_exceeds_remaining_tokens(
        self, use_case, user_with_router_access, router
    ):
        # Arrange
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        rate_limit_state.tpm = TpmRateLimitState(value=100, remaining=9, reset=0)
        use_case.router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state

        # Act
        result = await use_case._check_rate_limits(authenticated_user=user_with_router_access, router=router, prompt_tokens=10)

        # Assert
        assert isinstance(result, RouterRateLimitExceededError)
        assert result.id == router.id
        assert result.limit_type == LimitType.TPM
        assert result.headers == rate_limit_state.build_limit_headers
        use_case.router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=router.id,
        )

    @pytest.mark.asyncio
    async def test_should_update_rate_limit_state_when_non_admin_user_is_within_limits(self, use_case, user_with_router_access, router):
        # Arrange
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        use_case.router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state

        # Act
        result = await use_case._check_rate_limits(authenticated_user=user_with_router_access, router=router, prompt_tokens=1)

        # Assert
        assert result is rate_limit_state
        use_case.router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=router.id,
            prompt_tokens=1,
        )


class TestSendRequest:
    @pytest.fixture(autouse=True)
    def configure_provider_flow(self, use_case, provider, sample_data):
        use_case.provider_repository.get_all_providers_of_router.return_value = [provider]
        use_case.provider_load_balancer.find_best_provider.return_value = provider
        use_case.provider_metrics_logger.increment_inflight.return_value = True
        use_case.provider_client.forward_request.return_value = ProviderOriginalResponse(data={})
        use_case.provider_adapter_builder.build.return_value = _mock_adapter(formatted_response=sample_data)

    @pytest.mark.asyncio
    async def test_should_return_request_validation_error_without_forwarding_when_request_is_invalid(self, use_case, router, provider, payload):
        # Arrange
        validation_error = ProviderAdapterValidationRequestError(provider_type=ProviderType.VLLM, errors=[{"msg": "invalid"}])
        use_case.provider_adapter_builder.build.return_value = _mock_adapter(request_error=validation_error)

        # Act
        result = await use_case._send_request(router=router, prompt_tokens=1, payload=payload)

        # Assert
        assert result == validation_error
        use_case.provider_adapter_builder.build.assert_called_once_with(endpoint=ForwardingTestUseCase.ENDPOINT, provider=provider)
        use_case.provider_metrics_logger.increment_inflight.assert_not_awaited()
        use_case.provider_client.forward_request.assert_not_awaited()
        use_case.usage_recorder.record_provider.assert_called_once_with(provider_id=provider.id, provider_model_name=provider.model_name)
        use_case.usage_recorder.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_forward_error_and_decrement_inflight_when_provider_call_fails(self, use_case, router, provider, payload):
        # Arrange
        provider_error = TooBusyModelError(status_code=503, detail="busy")
        use_case.provider_client.forward_request.return_value = provider_error

        # Act
        result = await use_case._send_request(router=router, prompt_tokens=1, payload=payload)

        # Assert
        assert result == provider_error
        use_case.provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=provider.id)
        use_case.usage_recorder.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_response_validation_error_without_decrementing_when_inflight_was_not_incremented(self, use_case, router, payload):
        # Arrange
        use_case.provider_metrics_logger.increment_inflight.return_value = False
        validation_error = ProviderAdapterValidationResponseError(provider_type=ProviderType.VLLM, errors=[{"msg": "invalid"}])
        use_case.provider_adapter_builder.build.return_value = _mock_adapter(response_error=validation_error)

        # Act
        result = await use_case._send_request(router=router, prompt_tokens=1, payload=payload)

        # Assert
        assert result == validation_error
        use_case.provider_metrics_logger.decrement_inflight.assert_not_called()
        use_case.usage_recorder.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_enrich_usage_and_log_metrics_when_formatted_response_has_data(
        self, use_case, router, provider, sample_data, payload, model_tokenizer, model_environmental_impacts_computer
    ):
        # Arrange
        with patch("api.use_cases._providerrequestforwardingusecase.time.perf_counter", side_effect=[0, 0.12]):
            with patch("api.domain.usage.entities.Usage.compute_request_cost", return_value=0.03) as compute_request_cost:
                # Act
                result = await use_case._send_request(router=router, prompt_tokens=1, payload=payload)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert result.data is sample_data
        assert result.data.usage == Usage(
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            cost=0.03,
            impacts=EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0),
        )
        use_case.provider_repository.get_all_providers_of_router.assert_awaited_once_with(router_id=router.id)
        use_case.provider_load_balancer.find_best_provider.assert_awaited_once_with(
            strategy=router.load_balancing_strategy,
            providers=[provider],
        )
        original_request = use_case.provider_adapter_builder.build.return_value.format_request.call_args.kwargs["original_request"]
        assert original_request.endpoint == ForwardingTestUseCase.ENDPOINT
        assert original_request.payload == payload
        use_case.provider_metrics_logger.log_metric.assert_awaited_once_with(provider_id=provider.id, metric=Metric.LATENCY, value=120)
        use_case.provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=provider.id)
        model_tokenizer.compute_tokens.assert_called_once_with(texts=["world"])
        model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=provider.model_active_params,
            model_total_params=provider.model_total_params,
            model_zone=provider.model_hosting_zone,
            completion_tokens=1,
            request_latency=120,
        )
        compute_request_cost.assert_called_once_with(
            prompt_tokens=1,
            completion_tokens=1,
            cost_prompt_tokens=router.cost_prompt_tokens,
            cost_completion_tokens=router.cost_completion_tokens,
        )
        use_case.usage_recorder.record_usage.assert_called_once_with(
            request_id=sample_data.id,
            prompt_tokens=1,
            completion_tokens=1,
            cost=0.03,
        )

    @pytest.mark.asyncio
    async def test_should_record_usage_without_attaching_it_when_formatted_response_has_no_data(self, use_case, router, provider, payload):
        # Arrange
        use_case.provider_adapter_builder.build.return_value = _mock_adapter(formatted_text="hello world")

        # Act
        with patch("api.use_cases._providerrequestforwardingusecase.time.perf_counter", side_effect=[0, 0.12]):
            with patch("api.domain.usage.entities.Usage.compute_request_cost", return_value=0.03):
                result = await use_case._send_request(router=router, prompt_tokens=1, payload=payload)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert result.data is None
        use_case.usage_recorder.record_usage.assert_called_once_with(
            request_id="req-1",
            prompt_tokens=1,
            completion_tokens=1,
            cost=0.03,
        )


class TestExecute:
    @pytest.fixture(autouse=True)
    def mock_collaborator_methods(self, use_case, router, sample_data):
        formatted_response = ProviderFormattedResponse(id=sample_data.id, data=sample_data)
        use_case._resolve_router = AsyncMock(return_value=router)
        use_case._check_rate_limits = AsyncMock(return_value=RouterRateLimitState.admin_rate_limit_state())
        use_case._send_request = AsyncMock(return_value=formatted_response)

    @pytest.fixture
    def command(self, admin_user):
        return ForwardingTestCommand(payload=ForwardingTestPayload(), authenticated_user=admin_user)

    @pytest.mark.asyncio
    async def test_should_return_resolve_router_error_without_checking_rate_limits_or_sending(self, use_case, command, admin_user):
        # Arrange
        error = RouterNotFoundError(name="test-router")
        use_case._resolve_router.return_value = error

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result is error
        use_case._resolve_router.assert_awaited_once_with(authenticated_user=admin_user, model_name_or_alias="test-router")
        use_case.model_tokenizer.compute_tokens.assert_not_called()
        use_case._check_rate_limits.assert_not_awaited()
        use_case._send_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_rate_limit_error_without_sending_request(self, use_case, command, admin_user, router):
        # Arrange
        error = RouterRateLimitExceededError(id=router.id, limit_type=LimitType.RPM, headers={})
        use_case._check_rate_limits.return_value = error

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result is error
        use_case.model_tokenizer.compute_tokens.assert_called_once_with(texts=["hello"])
        use_case._check_rate_limits.assert_awaited_once_with(authenticated_user=admin_user, router=router, prompt_tokens=1)
        use_case._send_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_send_request_error(self, use_case, command, router):
        # Arrange
        error = TooBusyModelError(status_code=503, detail="busy")
        use_case._send_request.return_value = error

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result is error
        use_case._send_request.assert_awaited_once_with(router=router, prompt_tokens=1, payload=command.payload)

    @pytest.mark.asyncio
    async def test_should_return_success_with_formatted_data_and_rate_limit_headers(self, use_case, command, sample_data):
        # Arrange
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        use_case._check_rate_limits.return_value = rate_limit_state

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, ProviderRequestForwardingUseCaseSuccess)
        assert result.data is sample_data
        assert result.headers == rate_limit_state.build_limit_headers
