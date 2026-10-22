from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import ClassVar

from pydantic import BaseModel

from api.domain import ForwardablePayload
from api.domain.key.entities import Key
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import Provider, ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.provider.errors import (
    NoAvailableProviderError,
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    UnsupportedProviderEndpointError,
)
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.usage import UsageContext, UsageRepository
from api.domain.usage.entities import BilledTokens, PromptTokensDetails, Usage
from api.domain.user.errors import UserHasNoAccessToRouterError
from api.domain.user.views import AuthenticatedUserView


class ForwardingCommand[TPayload: ForwardablePayload](BaseModel):
    payload: TPayload
    authenticated_user: AuthenticatedUserView
    authenticated_key: Key

    @property
    def model(self) -> str | None:
        return self.payload.model

    def get_prompts(self) -> list[str]:
        return self.payload.get_prompts()


@dataclass
class ProviderRequestForwardingUseCaseSuccess[TData]:
    data: TData
    headers: dict[str, str]


type ProviderRequestForwardingUseCaseError = (
    NoAvailableProviderError
    | ProviderAdapterValidationRequestError
    | ProviderAdapterValidationResponseError
    | RouterRateLimitExceededError
    | RouterNotFoundError
    | RouterHasNoProvidersError
    | RouterHasWrongTypeError
    | TooBusyModelError
    | StatusCodeModelError
    | UnknownModelError
    | UnsupportedProviderEndpointError
    | UserHasNoAccessToRouterError
)
type ProviderRequestForwardingUseCaseResult[TData] = ProviderRequestForwardingUseCaseSuccess[TData] | ProviderRequestForwardingUseCaseError


class ProviderRequestForwardingUseCase[TCommand: ForwardingCommand, TResult]:
    ROUTER_TYPE: ClassVar[RouterType]
    ENDPOINT: ClassVar[ProviderEndpoint]

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
        usage_context: UsageContext,
        usage_repository: UsageRepository,
    ) -> None:
        self.model_environmental_impacts_computer = model_environmental_impacts_computer
        self.model_tokenizer = model_tokenizer
        self.provider_client = provider_client
        self.provider_load_balancer = provider_load_balancer
        self.provider_metrics_logger = provider_metrics_logger
        self.provider_repository = provider_repository

        self.router_rate_limiter = router_rate_limiter
        self.router_repository = router_repository

        self.usage_context = usage_context
        self.usage_repository = usage_repository

    async def execute(self, command: TCommand) -> TResult:
        authenticated_user = command.authenticated_user

        if (error := self._check_command(command=command)) is not None:
            return error

        result = await self._get_usable_router(authenticated_user=authenticated_user, model_name_or_alias=command.model)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        estimated_prompt_tokens = self.model_tokenizer.compute_tokens(texts=command.get_prompts())

        result = await self._get_remaining_rate_limits(
            authenticated_user=authenticated_user, router=router, estimated_prompt_tokens=estimated_prompt_tokens
        )
        match result:
            case RouterRateLimitState() as remaining_rate_limits:
                pass
            case error:
                return error

        result = await self._forward_request_to_provider(
            authenticated_user=authenticated_user,
            router=router,
            estimated_prompt_tokens=estimated_prompt_tokens,
            payload=command.payload,
            request_id=self.usage_context.get_request_id(),
        )
        match result:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return error

        return self._build_success(
            command=command, response=provider_response, headers=remaining_rate_limits.build_limit_headers(estimated_prompt_tokens)
        )

    def _check_command(self, command: TCommand) -> TResult | None:
        return None

    async def _get_usable_router(
        self,
        authenticated_user: AuthenticatedUserView,
        model_name_or_alias: str,
    ) -> Router | RouterNotFoundError | RouterHasNoProvidersError | RouterHasWrongTypeError | UserHasNoAccessToRouterError:
        result = await self.router_repository.get_router_by_name_or_alias(name_or_alias=model_name_or_alias)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        self.usage_context.record_router(router_id=router.id, router_name=router.name)

        if router.has_no_providers:
            return RouterHasNoProvidersError(id=router.id)
        if router.type != self.ROUTER_TYPE:
            return RouterHasWrongTypeError(id=router.id, actual_type=router.type, expected_type=self.ROUTER_TYPE)
        if authenticated_user.cannot_access_router(router_id=router.id):
            return UserHasNoAccessToRouterError(id=router.id)

        return router

    async def _get_remaining_rate_limits(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        estimated_prompt_tokens: int,
    ) -> RouterRateLimitState | RouterRateLimitExceededError:
        if authenticated_user.is_admin:
            return RouterRateLimitState.unlimited()

        remaining_rate_limits = await self.router_rate_limiter.get_rate_limit_state(
            user_id=authenticated_user.id,
            router_limits=authenticated_user.limits_for(router_id=router.id),
            router_id=router.id,
        )
        exceeded_limit_types = remaining_rate_limits.exceeded_limits(prompt_tokens=estimated_prompt_tokens)
        if exceeded_limit_types:
            return RouterRateLimitExceededError(
                id=router.id,
                limit_type=exceeded_limit_types[0],
                headers=remaining_rate_limits.build_limit_headers(estimated_prompt_tokens, charged=False),
            )

        return remaining_rate_limits

    async def _forward_request_to_provider(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        estimated_prompt_tokens: int,
        payload: ForwardablePayload,
        request_id: str,
    ) -> (
        ProviderResponse
        | ProviderAdapterValidationRequestError
        | TooBusyModelError
        | UnknownModelError
        | StatusCodeModelError
        | ProviderAdapterValidationResponseError
        | UnsupportedProviderEndpointError
    ):
        provider = await self._select_provider(router=router)
        request = ProviderRequest(id=request_id, endpoint=self.ENDPOINT, payload=payload)

        async with self._count_ongoing_request(provider=provider):
            result = await self.provider_client.forward(provider=provider, request=request)
            latency = self.usage_context.elapsed_ms()

        match result:
            case ProviderResponse() as provider_response:
                billed_tokens = self._get_billed_tokens(
                    estimated_prompt_tokens=estimated_prompt_tokens,
                    completions=provider_response.get_completions(),
                    provider_usage=provider_response.get_usage(),
                )
                usage = self._compute_usage(provider=provider, router=router, billed_tokens=billed_tokens, latency=latency)

                provider_response = provider_response.with_usage(usage)

            case error:
                return error

        self._record_and_save_usage(usage=usage, latency=latency)
        self._charge_rate_limits(authenticated_user=authenticated_user, router=router, usage=usage)

        return provider_response

    async def _select_provider(self, router: Router) -> Provider:
        providers = await self.provider_repository.get_all_providers_of_router(router_id=router.id)
        provider = await self.provider_load_balancer.find_best_provider(strategy=router.load_balancing_strategy, providers=providers)
        self.usage_context.record_provider(provider_id=provider.id, provider_model_name=provider.model_name)

        return provider

    @asynccontextmanager
    async def _count_ongoing_request(self, provider: Provider) -> AsyncIterator[None]:
        is_incremented = await self.provider_metrics_logger.increment_inflight(provider_id=provider.id)
        try:
            yield
        finally:
            if is_incremented:
                await self.provider_metrics_logger.decrement_inflight(provider_id=provider.id)

    def _get_billed_tokens(self, estimated_prompt_tokens: int, completions: list[str], provider_usage: Usage | None) -> BilledTokens:
        if provider_usage is None:
            return BilledTokens(prompt_tokens=estimated_prompt_tokens, completion_tokens=self.model_tokenizer.compute_tokens(texts=completions))

        return BilledTokens(
            prompt_tokens=provider_usage.prompt_tokens,
            completion_tokens=provider_usage.completion_tokens,
            cached_tokens=provider_usage.prompt_tokens_details.cached_tokens,
        )

    def _compute_usage(self, provider: Provider, router: Router, billed_tokens: BilledTokens, latency: int) -> Usage:
        environmental_impacts = self.model_environmental_impacts_computer.compute(
            model_active_params=provider.model_active_params,
            model_total_params=provider.model_total_params,
            model_zone=provider.model_hosting_zone,
            completion_tokens=billed_tokens.completion_tokens,
            request_latency=latency,
        )
        cost = Usage.compute_request_cost(
            prompt_tokens=billed_tokens.prompt_tokens,
            completion_tokens=billed_tokens.completion_tokens,
            cost_prompt_tokens=router.cost_prompt_tokens,
            cost_completion_tokens=router.cost_completion_tokens,
        )

        return Usage(
            prompt_tokens=billed_tokens.prompt_tokens,
            completion_tokens=billed_tokens.completion_tokens,
            total_tokens=billed_tokens.prompt_tokens + billed_tokens.completion_tokens,
            cost=cost,
            impacts=environmental_impacts,
            prompt_tokens_details=PromptTokensDetails(cached_tokens=billed_tokens.cached_tokens),
        )

    def _record_and_save_usage(self, usage: Usage, latency: int, ttft: int | None = None) -> None:
        self.usage_context.record_usage(usage=usage, latency=latency, ttft=ttft)
        self.usage_repository.save_record(record=self.usage_context.get_record())

    def _charge_rate_limits(self, authenticated_user: AuthenticatedUserView, router: Router, usage: Usage) -> None:
        if authenticated_user.is_admin:
            return

        self.router_rate_limiter.update_rate_limit_state(
            user_id=authenticated_user.id,
            router_limits=authenticated_user.limits_for(router_id=router.id),
            router_id=router.id,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cached_tokens=usage.prompt_tokens_details.cached_tokens,
        )

    def _build_success(self, command: TCommand, response: ProviderResponse, headers: dict[str, str]) -> TResult:
        return ProviderRequestForwardingUseCaseSuccess(data=response.data, headers=headers)
