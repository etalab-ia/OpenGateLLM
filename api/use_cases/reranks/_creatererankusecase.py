from contextvars import ContextVar
from dataclasses import dataclass
import time
from typing import Any

from pydantic import ConfigDict

from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import ProviderAdapterBuilder, ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import Router, RouterRateLimitState
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserHasNoAccessToRouterError
from api.infrastructure.fastapi.context import RequestContext
from api.schemas.core.models import Metric
from api.utils.variables import EndpointRoute


class CreateRerankCommand(CreateRerankBody):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    request_context: ContextVar[RequestContext]

    def set_value_in_request_context(self, key: str, value: Any) -> None:
        setattr(self.request_context.get(), key, value)


@dataclass
class CreateRerankUseCaseSuccess:
    data: Rerank
    headers: dict[str, str]


type CreateRerankUseCaseResult = (
    CreateRerankUseCaseSuccess
    | NoAvailableProviderError
    | ProviderAdapterValidationRequestError
    | ProviderAdapterValidationResponseError
    | RouterRateLimitExceededError
    | RouterNotFoundError
    | RouterHasNoProvidersError
    | RouterHasWrongTypeError
    | TooBusyModelError
    | StatusCodeModelError
    | UnknownModelError
    | UserExpiredError
    | UserHasNoAccessToRouterError
)


class CreateRerankUseCase:
    def __init__(
        self,
        model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer,
        model_tokenizer: ModelTokenizer,
        provider_adapter_builder: ProviderAdapterBuilder,
        provider_client: ProviderClient,
        provider_load_balancer: ProviderLoadBalancer,
        provider_metrics_logger: ProviderMetricsLogger,
        provider_repository: ProviderRepository,
        router_rate_limiter: RouterRateLimiter,
        router_repository: RouterRepository,
        user_with_role_query: UserWithRoleQuery,
    ) -> None:
        self.model_environmental_impacts_computer = model_environmental_impacts_computer
        self.model_tokenizer = model_tokenizer

        self.provider_adapter_builder = provider_adapter_builder
        self.provider_client = provider_client
        self.provider_load_balancer = provider_load_balancer
        self.provider_metrics_logger = provider_metrics_logger
        self.provider_repository = provider_repository

        self.router_rate_limiter = router_rate_limiter
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: CreateRerankCommand) -> CreateRerankUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.request_context.get().user_id)
        command.set_value_in_request_context(key="user_email", value=user.email)

        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        result = await self.router_repository.get_router_by_name_or_alias(name_or_alias=command.model)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        command.set_value_in_request_context(key="router_id", value=router.id)
        command.set_value_in_request_context(key="router_name", value=router.name)

        if router.has_no_providers:
            return RouterHasNoProvidersError(id=router.id)
        if router.type != RouterType.TEXT_CLASSIFICATION:
            return RouterHasWrongTypeError(id=router.id, actual_type=router.type, expected_type=RouterType.TEXT_CLASSIFICATION)
        if user.cannot_access_router(router_id=router.id):
            return UserHasNoAccessToRouterError(id=router.id)

        providers = await self.provider_repository.get_all_providers_of_router(router_id=router.id)
        provider = await self.provider_load_balancer.find_best_provider(strategy=router.load_balancing_strategy, providers=providers)

        command.set_value_in_request_context(key="provider_id", value=provider.id)
        command.set_value_in_request_context(key="provider_model_name", value=provider.model_name)

        adapter = self.provider_adapter_builder.build(
            cost_completion_tokens=router.cost_completion_tokens,
            cost_prompt_tokens=router.cost_prompt_tokens,
            endpoint=EndpointRoute.RERANK,
            provider=provider,
        )
        original_request = ProviderOriginalRequest(
            endpoint=EndpointRoute.RERANK,
            body=CreateRerankBody(query=command.query, documents=command.documents, model=command.model, top_n=command.top_n),
        )
        prompt_tokens = adapter.compute_prompt_tokens(original_request=original_request)

        if not user.is_admin:
            limits = [limit for limit in user.limits if limit.router_id == router.id]
            rate_limit_state = await self.router_rate_limiter.get_rate_limit_state(
                user_id=user.id,
                router_limits=limits,
                router_id=router.id,
                prompt_tokens=prompt_tokens,
            )
            exceeded_limits = rate_limit_state.exceeded_limits
            if exceeded_limits:
                limit_type = exceeded_limits[0]
                return RouterRateLimitExceededError(id=router.id, limit_type=limit_type, headers=rate_limit_state.build_limit_headers)
            await self.router_rate_limiter.update_rate_limit_state(
                user_id=user.id,
                router_limits=limits,
                router_id=router.id,
                prompt_tokens=prompt_tokens,
            )
        else:
            rate_limit_state = RouterRateLimitState.admin_rate_limit_state()

        match adapter.format_request(original_request=original_request):
            case ProviderFormattedRequest() as formatted_request:
                pass
            case ProviderAdapterValidationRequestError() as error:
                return error

        inflight_is_incremented = await self.provider_metrics_logger.increment_inflight(provider_id=provider.id)

        start_time = time.perf_counter()
        result = await self.provider_client.forward_request(provider=provider, formatted_request=formatted_request)
        latency = int((time.perf_counter() - start_time) * 1000)  # ms

        if inflight_is_incremented:
            await self.provider_metrics_logger.decrement_inflight(provider_id=provider.id)

        match result:
            case ProviderOriginalResponse() as original_response:
                pass
            case error:
                return error

        result = adapter.format_response(
            original_request=original_request,
            original_response=original_response,
            prompt_tokens=prompt_tokens,
            latency=latency,
        )
        match result:
            case ProviderFormattedResponse() as formatted_response:
                await self.provider_metrics_logger.log_metric(
                    provider_id=provider.id,
                    metric=Metric.LATENCY,
                    value=latency,
                )
                await self.provider_metrics_logger.log_metric(
                    provider_id=provider.id,
                    metric=Metric.NORMALIZED_LATENCY,
                    value=latency,  # normalized = latency because rerank has no completion tokens
                )
            case ProviderAdapterValidationResponseError() as error:
                return error

        command.set_value_in_request_context(key="id", value=formatted_response.data.id)
        command.set_value_in_request_context(key="prompt_tokens", value=prompt_tokens)
        command.set_value_in_request_context(key="total_tokens", value=prompt_tokens)
        command.set_value_in_request_context(key="cost", value=formatted_response.data.usage.cost)

        return CreateRerankUseCaseSuccess(data=formatted_response.data, headers=rate_limit_state.build_limit_headers)
