import datetime as dt
from http import HTTPMethod
from unittest.mock import AsyncMock, MagicMock, call, create_autospec, patch

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import TooBusyModelError
from api.domain.ocr.entities import OCR, CreateOCRBody, OCRDocumentURLChunk, OCRPageObject, OCRUsage
from api.domain.provider import ProviderAdapter
from api.domain.provider.entities import (
    Metric,
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalResponse,
    ProviderType,
    ResponseMetrics,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.role.entities import Limit, LimitType
from api.domain.router.entities import RouterRateLimitState, RpdRateLimitState, RpmRateLimitState, TpdRateLimitState, TpmRateLimitState
from api.domain.router.errors import (
    RouterHasNoProvidersError,
    RouterHasWrongTypeError,
    RouterNotFoundError,
    RouterRateLimitExceededError,
)
from api.domain.usage import UsageRecorder
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases.ocr import CreateOCRCommand, CreateOCRUseCase, CreateOCRUseCaseSuccess


@pytest.fixture
def model_tokenizer():
    tokenizer = MagicMock()
    tokenizer.compute_tokens.return_value = 0
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
def usage_recorder():
    return create_autospec(UsageRecorder, instance=True, spec_set=True)


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
    usage_recorder,
    ocr_router,
    ocr_provider,
    sample_ocr,
) -> CreateOCRUseCase:
    router_repository.get_router_by_name_or_alias.return_value = ocr_router
    provider_repository.get_all_providers_of_router.return_value = [ocr_provider]
    provider_load_balancer.find_best_provider.return_value = ocr_provider
    provider_metrics_logger.increment_inflight.return_value = True
    provider_client.forward_request.return_value = ProviderOriginalResponse(data={})
    rate_limit_state = rate_limit_state_factory()
    rate_limit_state.rpm = RpmRateLimitState(value=100, remaining=99, reset=int(dt.datetime.now(dt.UTC).timestamp()) + 30)
    router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state
    mock_adapter = _mock_adapter(formatted_response=sample_ocr)
    provider_adapter_builder.build.return_value = mock_adapter

    return CreateOCRUseCase(
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


@pytest.fixture
def admin_user():
    return AuthenticatedUserFactory(id=1, admin=True)


@pytest.fixture
def user_with_router_access():
    return AuthenticatedUserFactory(id=1, without_permission=True, limits=[Limit(router_id=1, type=LimitType.RPM, value=100)])


@pytest.fixture
def make_command():
    def _make(user) -> CreateOCRCommand:
        return CreateOCRCommand(
            body=CreateOCRBody(
                document=OCRDocumentURLChunk(document_url="https://example.com/document.pdf"),
                model="ocr-router",
            ),
            authenticated_user=user,
        )

    return _make


@pytest.fixture
def default_command(make_command, admin_user):
    return make_command(admin_user)


@pytest.fixture
def user_without_router_access():
    return AuthenticatedUserFactory(id=1, without_permission=True, limits=[])


@pytest.fixture
def ocr_router():
    return RouterFactory(
        id=1,
        name="ocr-router",
        type=RouterType.IMAGE_TO_TEXT,
        providers=1,
        load_balancing_strategy="shuffle",
    )


@pytest.fixture
def ocr_provider():
    return ProviderFactory(id=1, router_id=1, type=ProviderType.MISTRAL, model_name="mistral-ocr")


@pytest.fixture
def sample_ocr():
    return OCR(
        id="ocr-1",
        model="ocr-router",
        pages=[OCRPageObject(index=0, images=[], markdown="# Document")],
        usage_info=OCRUsage(pages_processed=1),
    )


@pytest.fixture
def mock_ocr_latency_120ms():
    with patch(
        "api.use_cases._forwarding.time.perf_counter",
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
def mock_successful_ocr_flow(mock_ocr_latency_120ms, mock_usage_cost):
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


def assert_recorded(
    usage_recorder,
    request_id: str | None = None,
    router_id: int | None = None,
    router_name: str | None = None,
    provider_id: int | None = None,
    provider_model_name: str | None = None,
    prompt_tokens: int | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
):
    if router_id is None:
        usage_recorder.record_router.assert_not_called()
    else:
        usage_recorder.record_router.assert_called_once_with(router_id=router_id, router_name=router_name)

    if provider_id is None:
        usage_recorder.record_provider.assert_not_called()
    else:
        usage_recorder.record_provider.assert_called_once_with(provider_id=provider_id, provider_model_name=provider_model_name)

    if prompt_tokens is None:
        usage_recorder.record_usage.assert_not_called()
    else:
        usage_recorder.record_usage.assert_called_once_with(
            request_id=request_id,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )


def _mock_adapter(*, formatted_request=None, formatted_response=None, request_error=None, response_error=None):
    adapter = create_autospec(ProviderAdapter, instance=True, spec_set=True)
    adapter.format_request.return_value = formatted_request or ProviderFormattedRequest(
        method=HTTPMethod.POST,
        url="https://provider.example/ocr",
        body={},
    )
    adapter.format_response.return_value = response_error or ProviderFormattedResponse(data=formatted_response, metrics=ResponseMetrics(latency=120))
    if request_error is not None:
        adapter.format_request.return_value = request_error
    return adapter


class TestCreateOCRUseCase:
    @pytest.mark.asyncio
    async def test_should_return_router_not_found_error_when_router_does_not_exist(self, use_case, default_command, admin_user):
        # Arrange
        use_case.router_repository.get_router_by_name_or_alias.return_value = RouterNotFoundError(name="ocr-router")

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterNotFoundError)

        assert_recorded(use_case.usage_recorder)

    @pytest.mark.asyncio
    async def test_should_return_router_has_no_providers_error_when_router_has_no_providers(self, use_case, default_command, admin_user):
        # Arrange
        ocr_router = RouterFactory(id=1, name="ocr-router", type=RouterType.IMAGE_TO_TEXT, providers=0)
        use_case.router_repository.get_router_by_name_or_alias.return_value = ocr_router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterHasNoProvidersError)
        assert result.id == 1

        assert_recorded(use_case.usage_recorder, router_id=ocr_router.id, router_name=ocr_router.name)

    @pytest.mark.asyncio
    async def test_should_return_router_has_wrong_type_error_when_router_is_not_image_to_text(self, use_case, default_command, admin_user):
        # Arrange
        ocr_router = RouterFactory(id=1, name="ocr-router", type=RouterType.TEXT_GENERATION, providers=1)
        use_case.router_repository.get_router_by_name_or_alias.return_value = ocr_router

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, RouterHasWrongTypeError)
        assert result.actual_type == RouterType.TEXT_GENERATION
        assert result.expected_type == RouterType.IMAGE_TO_TEXT

        assert_recorded(use_case.usage_recorder, router_id=ocr_router.id, router_name=ocr_router.name)

    @pytest.mark.asyncio
    async def test_should_return_user_has_insufficient_budget_error_when_router_is_paid_and_user_budget_is_zero(
        self, use_case, user_with_router_access, provider_load_balancer, provider_repository, make_command
    ):
        # Arrange
        user_with_zero_budget = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            budget=0,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        command = make_command(user_with_zero_budget)
        paid_ocr_router = RouterFactory(
            id=1,
            name="ocr-router",
            type=RouterType.IMAGE_TO_TEXT,
            providers=1,
            load_balancing_strategy="shuffle",
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = paid_ocr_router

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UserHasInsufficientBudgetError)
        provider_repository.get_all_providers_of_router.assert_not_awaited()
        provider_load_balancer.find_best_provider.assert_not_awaited()

        assert_recorded(
            use_case.usage_recorder,
            router_id=paid_ocr_router.id,
            router_name=paid_ocr_router.name,
        )

    @pytest.mark.asyncio
    async def test_should_return_insufficient_budget_when_router_bills_completion_only_and_user_budget_is_zero(
        self, use_case, user_with_router_access, provider_load_balancer, provider_repository, make_command
    ):
        # OCR produces completion tokens, so a completion-only-priced router must gate on budget too.
        # Arrange
        user_with_zero_budget = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            budget=0,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        command = make_command(user_with_zero_budget)
        completion_only_router = RouterFactory(
            id=1,
            name="ocr-router",
            type=RouterType.IMAGE_TO_TEXT,
            providers=1,
            load_balancing_strategy="shuffle",
            cost_prompt_tokens=0.0,
            cost_completion_tokens=0.002,
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = completion_only_router

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UserHasInsufficientBudgetError)
        provider_repository.get_all_providers_of_router.assert_not_awaited()
        provider_load_balancer.find_best_provider.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_not_check_budget_when_router_is_free(
        self, use_case, user_with_router_access, provider_load_balancer, make_command, mock_successful_ocr_flow
    ):
        # Arrange
        user_with_zero_budget = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            budget=0,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        command = make_command(user_with_zero_budget)
        free_ocr_router = RouterFactory(
            id=1,
            name="ocr-router",
            type=RouterType.IMAGE_TO_TEXT,
            providers=1,
            load_balancing_strategy="shuffle",
            free=True,
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = free_ocr_router

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateOCRUseCaseSuccess)
        provider_load_balancer.find_best_provider.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_not_check_budget_when_user_has_unlimited_budget_and_router_is_paid(
        self, use_case, user_with_router_access, provider_load_balancer, make_command, mock_successful_ocr_flow
    ):
        # Arrange
        user_with_unlimited_budget = AuthenticatedUserFactory(
            id=user_with_router_access.id,
            without_permission=True,
            unlimited_budget=True,
            limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
        )
        command = make_command(user_with_unlimited_budget)
        paid_ocr_router = RouterFactory(
            id=1,
            name="ocr-router",
            type=RouterType.IMAGE_TO_TEXT,
            providers=1,
            load_balancing_strategy="shuffle",
            cost_prompt_tokens=0.001,
            cost_completion_tokens=0.002,
        )
        use_case.router_repository.get_router_by_name_or_alias.return_value = paid_ocr_router

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateOCRUseCaseSuccess)
        provider_load_balancer.find_best_provider.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_return_user_has_no_access_error_when_user_cannot_access_router(
        self, use_case, user_without_router_access, ocr_router, make_command
    ):
        # Arrange
        command = make_command(user_without_router_access)
        use_case.router_repository.get_router_by_name_or_alias.return_value = ocr_router

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, UserHasNoAccessToRouterError)
        assert result.id == ocr_router.id

        assert_recorded(use_case.usage_recorder, router_id=ocr_router.id, router_name=ocr_router.name)

    @pytest.mark.asyncio
    async def test_should_call_model_tokenizer_with_empty_prompts_before_rate_limit_check(
        self, use_case, user_with_router_access, model_tokenizer, make_command
    ):
        # Arrange
        command = make_command(user_with_router_access)
        use_case.router_rate_limiter.get_rate_limit_state.return_value = rate_limit_state_factory(rpm_exceeded=True)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, RouterRateLimitExceededError)
        model_tokenizer.compute_tokens.assert_called_once_with(texts=[])

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
        ocr_router,
        ocr_provider,
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
        assert result.id == ocr_router.id
        assert result.limit_type == limit_type
        assert result.headers == rate_limit_state.build_limit_headers
        router_rate_limiter.update_rate_limit_state.assert_not_called()
        provider_load_balancer.find_best_provider.assert_called_once()

        assert_recorded(
            use_case.usage_recorder,
            router_id=ocr_router.id,
            router_name=ocr_router.name,
            provider_id=ocr_provider.id,
            provider_model_name=ocr_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_provider_adapter_validation_request_error_when_request_is_invalid(
        self, use_case, provider_adapter_builder, ocr_router, ocr_provider, default_command, admin_user
    ):
        # Arrange
        validation_error = ProviderAdapterValidationRequestError(provider_type=ProviderType.MISTRAL, errors=[{"msg": "invalid"}])
        mock_adapter = _mock_adapter(request_error=validation_error)
        provider_adapter_builder.build.return_value = mock_adapter

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == validation_error

        assert_recorded(
            use_case.usage_recorder,
            router_id=ocr_router.id,
            router_name=ocr_router.name,
            provider_id=ocr_provider.id,
            provider_model_name=ocr_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_error_when_provider_forward_request_fails(
        self, use_case, provider_metrics_logger, provider_client, ocr_router, ocr_provider, default_command, admin_user
    ):
        # Arrange
        provider_error = TooBusyModelError(status_code=503, detail="busy")
        provider_client.forward_request.return_value = provider_error

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == provider_error
        provider_metrics_logger.decrement_inflight.assert_called_once_with(provider_id=ocr_provider.id)

        assert_recorded(
            use_case.usage_recorder,
            router_id=ocr_router.id,
            router_name=ocr_router.name,
            provider_id=ocr_provider.id,
            provider_model_name=ocr_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_provider_adapter_validation_response_error_when_response_is_invalid(
        self,
        use_case,
        provider_metrics_logger,
        provider_client,
        provider_adapter_builder,
        ocr_router,
        ocr_provider,
        default_command,
        admin_user,
    ):
        # Arrange
        provider_metrics_logger.increment_inflight.return_value = False
        provider_client.forward_request.return_value = ProviderOriginalResponse(data={}, metrics=ResponseMetrics(latency=80))
        validation_error = ProviderAdapterValidationResponseError(provider_type=ProviderType.MISTRAL, errors=[{"msg": "invalid"}])
        mock_adapter = _mock_adapter(response_error=validation_error)
        provider_adapter_builder.build.return_value = mock_adapter

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert result == validation_error
        provider_metrics_logger.decrement_inflight.assert_not_called()

        assert_recorded(
            use_case.usage_recorder,
            router_id=ocr_router.id,
            router_name=ocr_router.name,
            provider_id=ocr_provider.id,
            provider_model_name=ocr_provider.model_name,
        )

    @pytest.mark.asyncio
    async def test_should_return_ocr_when_admin_user_and_flow_succeeds(
        self,
        use_case,
        provider_repository,
        provider_load_balancer,
        provider_metrics_logger,
        ocr_router,
        ocr_provider,
        sample_ocr,
        router_rate_limiter,
        model_tokenizer,
        model_environmental_impacts_computer,
        default_command,
        admin_user,
        mock_successful_ocr_flow,
    ):
        # Arrange
        model_tokenizer.compute_tokens.side_effect = [0, 42]  # prompt tokens, then completion tokens (extracted markdown)

        # Act
        result = await use_case.execute(command=default_command)

        # Assert
        assert isinstance(result, CreateOCRUseCaseSuccess)
        assert result.data.id == sample_ocr.id
        assert result.data.pages == sample_ocr.pages
        assert result.data.model == sample_ocr.model
        assert result.data.usage_info == sample_ocr.usage_info
        assert result.data.usage == Usage(
            prompt_tokens=0,
            completion_tokens=42,
            total_tokens=42,
            cost=0.03,
            impacts=EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0),
        )
        assert result.headers == RouterRateLimitState.admin_rate_limit_state().build_limit_headers
        provider_repository.get_all_providers_of_router.assert_awaited_once_with(router_id=ocr_router.id)
        provider_load_balancer.find_best_provider.assert_awaited_once_with(
            strategy=ocr_router.load_balancing_strategy,
            providers=[ocr_provider],
        )
        provider_metrics_logger.log_metric.assert_has_awaits(
            [
                call(provider_id=ocr_provider.id, metric=Metric.LATENCY, value=120),
                call(provider_id=ocr_provider.id, metric=Metric.NORMALIZED_LATENCY, value=120),
            ]
        )
        provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=ocr_provider.id)
        model_tokenizer.compute_tokens.assert_has_calls([call(texts=[]), call(texts=["# Document"])])
        assert model_tokenizer.compute_tokens.call_count == 2
        model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=ocr_provider.model_active_params,
            model_total_params=ocr_provider.model_total_params,
            model_zone=ocr_provider.model_hosting_zone,
            completion_tokens=42,
            request_latency=120,
        )

        assert result.headers == rate_limit_state_factory().build_limit_headers
        router_rate_limiter.get_rate_limit_state.assert_not_awaited()
        router_rate_limiter.update_rate_limit_state.assert_not_awaited()

        assert_recorded(
            use_case.usage_recorder,
            request_id=sample_ocr.id,
            router_id=ocr_router.id,
            router_name=ocr_router.name,
            provider_id=ocr_provider.id,
            provider_model_name=ocr_provider.model_name,
            prompt_tokens=0,
            total_tokens=42,
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
        ocr_router,
        ocr_provider,
        sample_ocr,
        make_command,
        mock_successful_ocr_flow,
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
        mock_adapter = _mock_adapter(formatted_response=sample_ocr)
        provider_adapter_builder.build.return_value = mock_adapter
        model_tokenizer.compute_tokens.side_effect = [0, 42]  # prompt tokens, then completion tokens (extracted markdown)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateOCRUseCaseSuccess)
        assert result.data.id == sample_ocr.id
        assert result.data.pages == sample_ocr.pages
        assert result.data.model == sample_ocr.model
        assert result.data.usage == Usage(
            prompt_tokens=0,
            completion_tokens=42,
            total_tokens=42,
            cost=0.03,
            impacts=EnvironmentalImpacts(kgCO2eq=1.0, kWh=2.0),
        )
        assert result.headers == rate_limit_state.build_limit_headers
        provider_repository.get_all_providers_of_router.assert_awaited_once_with(router_id=ocr_router.id)
        provider_load_balancer.find_best_provider.assert_awaited_once_with(
            strategy=ocr_router.load_balancing_strategy,
            providers=[ocr_provider],
        )
        provider_metrics_logger.log_metric.assert_has_awaits(
            [
                call(provider_id=ocr_provider.id, metric=Metric.LATENCY, value=120),
                call(provider_id=ocr_provider.id, metric=Metric.NORMALIZED_LATENCY, value=120),
            ]
        )
        provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=ocr_provider.id)
        model_tokenizer.compute_tokens.assert_has_calls([call(texts=[]), call(texts=["# Document"])])
        assert model_tokenizer.compute_tokens.call_count == 2
        model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=ocr_provider.model_active_params,
            model_total_params=ocr_provider.model_total_params,
            model_zone=ocr_provider.model_hosting_zone,
            completion_tokens=42,
            request_latency=120,
        )

        assert result.headers == rate_limit_state.build_limit_headers
        router_rate_limiter.get_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=ocr_router.id,
            prompt_tokens=0,
        )
        router_rate_limiter.update_rate_limit_state.assert_awaited_once_with(
            user_id=user_with_router_access.id,
            router_limits=[Limit(router_id=1, type=LimitType.RPM, value=100)],
            router_id=ocr_router.id,
            prompt_tokens=0,
        )

        assert_recorded(
            use_case.usage_recorder,
            request_id=sample_ocr.id,
            router_id=ocr_router.id,
            router_name=ocr_router.name,
            provider_id=ocr_provider.id,
            provider_model_name=ocr_provider.model_name,
            prompt_tokens=0,
            total_tokens=42,
            cost=result.data.usage.cost,
        )
