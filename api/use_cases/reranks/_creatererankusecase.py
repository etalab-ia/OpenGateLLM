from contextvars import ContextVar
from dataclasses import dataclass
import time

from pydantic import ConfigDict

from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import Router, RouterRateLimitState
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user import UserWithRoleQuery
from api.domain.user.errors import UserExpiredError, UserHasNoAccessToRouterError
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.http.adapters.utils import build_adapter
from api.schemas.admin.roles import LimitType
from api.schemas.core.models import Metric
from api.utils.variables import EndpointRoute


class CreateRerankCommand(CreateRerankBody):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    request_context: ContextVar[RequestContext]


@dataclass
class CreateRerankUseCaseSuccess:
    rerank: Rerank
    rate_limit_state: RouterRateLimitState


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

        self.provider_client = provider_client
        self.provider_load_balancer = provider_load_balancer
        self.provider_metrics_logger = provider_metrics_logger
        self.provider_repository = provider_repository

        self.router_rate_limiter = router_rate_limiter
        self.router_repository = router_repository
        self.user_with_role_query = user_with_role_query

    async def execute(self, command: CreateRerankCommand) -> CreateRerankUseCaseResult:
        user = await self.user_with_role_query.get_user_with_role_by_id(user_id=command.request_context.get().user_id)
        if user.expires is not None and user.expires < time.time():
            return UserExpiredError()

        result = await self.router_repository.get_router_by_name_or_alias(name_or_alias=command.model)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        if router.has_no_providers:
            return RouterHasNoProvidersError(id=router.id)
        if router.type != RouterType.TEXT_CLASSIFICATION:
            return RouterHasWrongTypeError(id=router.id, type=router.type)
        if not user.is_admin or user.cannot_access_router(router_id=router.id):
            return UserHasNoAccessToRouterError(id=router.id)

        providers = await self.provider_repository.get_all_providers_of_router(router_id=router.id)
        provider = await self.provider_load_balancer.find_best_provider(strategy=router.load_balancing_strategy, providers=providers)

        adapter = build_adapter(
            cost_completion_tokens=router.cost_completion_tokens,
            cost_prompt_tokens=router.cost_prompt_tokens,
            endpoint=EndpointRoute.RERANK,
            model_environmental_impacts_computer=self.model_environmental_impacts_computer,
            model_tokenizer=self.model_tokenizer,
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
            exceeded_limits = rate_limit_state.exceeded_limits()
            if exceeded_limits:
                first_key = exceeded_limits[0]
                limit_type = LimitType(first_key) if isinstance(first_key, str) else first_key
                bucket = getattr(rate_limit_state, limit_type.value)
                return RouterRateLimitExceededError(
                    id=router.id,
                    limit_type=limit_type,
                    limit_value=bucket.value,
                    rate_limit_state=rate_limit_state,
                )
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
        result = await self.provider_client.forward_request(provider=provider, formatted_request=formatted_request)
        if inflight_is_incremented:
            await self.provider_metrics_logger.decrement_inflight(provider_id=provider.id)

        match result:
            case ProviderOriginalResponse() as original_response:
                await self.provider_metrics_logger.log_metric(provider_id=provider.id, metric=Metric.LATENCY, value=original_response.latency)
            case error:
                return error

        result = adapter.format_response(
            original_request=original_request,
            original_response=original_response,
            request_context=command.request_context,
            prompt_tokens=prompt_tokens,
        )
        match result:
            case ProviderFormattedResponse() as formatted_response:
                pass
            case ProviderAdapterValidationResponseError() as error:
                return error

        return CreateRerankUseCaseSuccess(rerank=formatted_response.data, rate_limit_state=rate_limit_state)
