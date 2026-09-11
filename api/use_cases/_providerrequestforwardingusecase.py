import asyncio
from dataclasses import dataclass
import math
import random
import time
from typing import ClassVar
from uuid import uuid4

from pydantic import BaseModel

from api.domain import ClientConnection, ForwardablePayload
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import (
    ProviderClient,
    ProviderLoadBalancer,
    ProviderMetricsLogger,
    ProviderQosAdmission,
    ProviderRepository,
    QosAdmissionFull,
    QosAdmissionGranted,
)
from api.domain.provider.entities import ProviderRequest, ProviderResponse
from api.domain.provider.errors import (
    ClientDisconnectedError,
    NoAvailableProviderError,
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    UnsupportedProviderEndpointError,
)
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.usage import UsageRecorder
from api.domain.usage.entities import Usage
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.domain.user.views import AuthenticatedUserView
from api.schemas.core.models import Metric
from api.utils.variables import CLIENT_DISCONNECT_POLL_SECONDS, QOS_WAIT_SLEEP_SECONDS, EndpointRoute


class ForwardingCommand[TPayload: ForwardablePayload](BaseModel):
    payload: TPayload
    authenticated_user: AuthenticatedUserView

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
    ClientDisconnectedError
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
    | UnsupportedProviderEndpointError
    | UserHasNoAccessToRouterError
    | UserHasInsufficientBudgetError
)
type ProviderRequestForwardingUseCaseResult[TData] = ProviderRequestForwardingUseCaseSuccess[TData] | ProviderRequestForwardingUseCaseError


class ProviderRequestForwardingUseCase[TCommand: ForwardingCommand, TData]:
    ROUTER_TYPE: ClassVar[RouterType]
    ENDPOINT: ClassVar[EndpointRoute]

    def __init__(
        self,
        model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer,
        model_tokenizer: ModelTokenizer,
        provider_client: ProviderClient,
        provider_load_balancer: ProviderLoadBalancer,
        provider_metrics_logger: ProviderMetricsLogger,
        provider_qos_admission: ProviderQosAdmission,
        provider_repository: ProviderRepository,
        router_rate_limiter: RouterRateLimiter,
        router_repository: RouterRepository,
        usage_recorder: UsageRecorder,
        client_connection: ClientConnection,
    ) -> None:
        self.model_environmental_impacts_computer = model_environmental_impacts_computer
        self.model_tokenizer = model_tokenizer
        self.provider_client = provider_client
        self.provider_load_balancer = provider_load_balancer
        self.provider_metrics_logger = provider_metrics_logger
        self.provider_qos_admission = provider_qos_admission
        self.provider_repository = provider_repository

        self.router_rate_limiter = router_rate_limiter
        self.router_repository = router_repository

        self.usage_recorder = usage_recorder
        self.client_connection = client_connection

    @staticmethod
    def compute_retry_after(qos_retry: int, depth: int) -> int:
        plafond = max(1, math.ceil(qos_retry * QOS_WAIT_SLEEP_SECONDS))
        retry_after = math.ceil((1 + depth) * (0.5 + random.random()))
        return max(1, min(plafond, retry_after))

    async def _resolve_router(
        self,
        authenticated_user: AuthenticatedUserView,
        model_name_or_alias: str,
    ) -> (
        Router
        | RouterNotFoundError
        | RouterHasNoProvidersError
        | RouterHasWrongTypeError
        | UserHasNoAccessToRouterError
        | UserHasInsufficientBudgetError
    ):
        result = await self.router_repository.get_router_by_name_or_alias(name_or_alias=model_name_or_alias)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        self.usage_recorder.record_router(router_id=router.id, router_name=router.name)

        if router.has_no_providers:
            return RouterHasNoProvidersError(id=router.id)
        if router.type != self.ROUTER_TYPE:
            return RouterHasWrongTypeError(id=router.id, actual_type=router.type, expected_type=self.ROUTER_TYPE)
        if authenticated_user.cannot_access_router(router_id=router.id):
            return UserHasNoAccessToRouterError(id=router.id)

        if router.is_billable and authenticated_user.has_insufficient_budget:
            return UserHasInsufficientBudgetError()

        return router

    async def _check_rate_limits(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        prompt_tokens: int,
    ) -> RouterRateLimitState | RouterRateLimitExceededError:

        if not authenticated_user.is_admin:
            limits = [limit for limit in authenticated_user.limits if limit.router_id == router.id]
            rate_limit_state = await self.router_rate_limiter.get_rate_limit_state(
                user_id=authenticated_user.id,
                router_limits=limits,
                router_id=router.id,
            )
            exceeded_limits = rate_limit_state.exceeded_limits(prompt_tokens=prompt_tokens)
            if exceeded_limits:
                limit_type = exceeded_limits[0]
                return RouterRateLimitExceededError(id=router.id, limit_type=limit_type, headers=rate_limit_state.build_limit_headers)
        else:
            rate_limit_state = RouterRateLimitState.admin_rate_limit_state()

        return rate_limit_state

    async def _send_request(
        self,
        router: Router,
        prompt_tokens: int,
        payload: ForwardablePayload,
    ) -> (
        ProviderResponse
        | ClientDisconnectedError
        | NoAvailableProviderError
        | ProviderAdapterValidationRequestError
        | TooBusyModelError
        | UnknownModelError
        | StatusCodeModelError
        | ProviderAdapterValidationResponseError
        | UnsupportedProviderEndpointError
    ):
        providers = await self.provider_repository.get_all_providers_of_router(router_id=router.id)
        request_id = str(uuid4())

        if not router.qos_enable:
            provider = await self.provider_load_balancer.find_best_provider(strategy=router.load_balancing_strategy, providers=providers)
            admitted = False
        else:
            admitted = True
            retries = 0
            while True:
                if await self.client_connection.is_disconnected():
                    return ClientDisconnectedError()
                admission_result = await self.provider_qos_admission.try_admit(
                    providers=providers,
                    strategy=router.load_balancing_strategy,
                    request_id=request_id,
                )
                match admission_result:
                    case QosAdmissionGranted(provider_id=provider_id):
                        provider = next(candidate for candidate in providers if candidate.id == provider_id)
                        break
                    case QosAdmissionFull(depth=depth):
                        if retries >= router.qos_retry:
                            return NoAvailableProviderError(
                                router_id=router.id,
                                retry_after=self.compute_retry_after(qos_retry=router.qos_retry, depth=depth),
                            )
                        await asyncio.sleep(QOS_WAIT_SLEEP_SECONDS)
                        retries += 1

        self.usage_recorder.record_provider(provider_id=provider.id, provider_model_name=provider.model_name)
        request = ProviderRequest(endpoint=self.ENDPOINT, payload=payload)

        if admitted:
            await self.provider_qos_admission.start_heartbeat(provider_id=provider.id, request_id=request_id)

        start_time = time.perf_counter()
        forward_task = asyncio.create_task(self.provider_client.forward(provider=provider, request=request))
        disconnect_task = asyncio.create_task(self._wait_until_disconnected())
        try:
            done, pending = await asyncio.wait({forward_task, disconnect_task}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            if forward_task not in done:
                return ClientDisconnectedError()

            result = forward_task.result()
            latency = int((time.perf_counter() - start_time) * 1000)  # ms
        finally:
            if admitted:
                await self.provider_qos_admission.release(provider_id=provider.id, request_id=request_id)

        match result:
            case ProviderResponse() as provider_response:
                completion_tokens = self.model_tokenizer.compute_tokens(texts=provider_response.get_completions())

                environmental_impacts = self.model_environmental_impacts_computer.compute(
                    model_active_params=provider.model_active_params,
                    model_total_params=provider.model_total_params,
                    model_zone=provider.model_hosting_zone,
                    completion_tokens=completion_tokens,
                    request_latency=latency,
                )
                cost = Usage.compute_request_cost(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_prompt_tokens=router.cost_prompt_tokens,
                    cost_completion_tokens=router.cost_completion_tokens,
                )

                if provider_response.data is not None:
                    provider_response.data.usage = Usage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=prompt_tokens + completion_tokens,
                        cost=cost,
                        impacts=environmental_impacts,
                    )

                await self.provider_metrics_logger.log_metric(
                    provider_id=provider.id,
                    metric=Metric.LATENCY,
                    value=latency,
                )
            case error:
                return error

        self.usage_recorder.record_usage(
            request_id=provider_response.id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
        )

        return provider_response

    async def _wait_until_disconnected(self) -> bool:
        while True:
            if await self.client_connection.is_disconnected():
                return True
            await asyncio.sleep(CLIENT_DISCONNECT_POLL_SECONDS)

    async def execute(self, command: TCommand) -> ProviderRequestForwardingUseCaseResult[TData]:
        authenticated_user = command.authenticated_user

        result = await self._resolve_router(authenticated_user=authenticated_user, model_name_or_alias=command.model)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        prompt_tokens = self.model_tokenizer.compute_tokens(texts=command.get_prompts())

        result = await self._check_rate_limits(authenticated_user=authenticated_user, router=router, prompt_tokens=prompt_tokens)
        match result:
            case RouterRateLimitState() as rate_limit_state:
                pass
            case error:
                return error

        result = await self._send_request(router=router, prompt_tokens=prompt_tokens, payload=command.payload)
        match result:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return error

        return ProviderRequestForwardingUseCaseSuccess(data=provider_response.data, headers=rate_limit_state.build_limit_headers)
