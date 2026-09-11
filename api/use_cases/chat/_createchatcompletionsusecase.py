from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from json import dumps
import time
from uuid import uuid4

from pydantic import ValidationError

from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk, CreateChatCompletionsBody
from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import Metric, Provider, ProviderRequest, ProviderResponse, ProviderStreamChunk
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.domain.search import SearchClient
from api.domain.search.entities import Search, SearchArgs, Searches
from api.domain.search.errors import SearchArgsValidationError, SearchStatusCodeError, SearchUnreachableError
from api.domain.usage import UsageRecorder
from api.use_cases._providerrequestforwardingusecase import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseError
from api.utils.variables import EndpointRoute

SEARCH_KEY_NAME = "_system_search_tool"
SEARCH_KEY_TTL = timedelta(hours=1)


class CreateChatCompletionsCommand(ForwardingCommand[CreateChatCompletionsBody]):
    @property
    def stream(self) -> bool:
        return self.payload.stream


@dataclass
class CreateChatCompletionsUseCaseSuccess:
    data: ChatCompletion
    headers: dict[str, str]


@dataclass
class CreateChatCompletionsStreamUseCaseSuccess:
    chunks: AsyncGenerator[ProviderStreamChunk]
    headers: dict[str, str]


type CreateChatCompletionsUseCaseResult = (
    CreateChatCompletionsUseCaseSuccess
    | CreateChatCompletionsStreamUseCaseSuccess
    | SearchArgsValidationError
    | SearchStatusCodeError
    | ProviderRequestForwardingUseCaseError
)


class CreateChatCompletionsUseCase(ProviderRequestForwardingUseCase[CreateChatCompletionsCommand, CreateChatCompletionsUseCaseResult]):
    ROUTER_TYPE = RouterType.TEXT_GENERATION
    ENDPOINT = EndpointRoute.CHAT_COMPLETIONS

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
        usage_recorder: UsageRecorder,
        key_repository: KeyRepository,
        search_client: SearchClient | None = None,
    ) -> None:
        super().__init__(
            model_environmental_impacts_computer=model_environmental_impacts_computer,
            model_tokenizer=model_tokenizer,
            provider_client=provider_client,
            provider_load_balancer=provider_load_balancer,
            provider_metrics_logger=provider_metrics_logger,
            provider_repository=provider_repository,
            router_rate_limiter=router_rate_limiter,
            router_repository=router_repository,
            usage_recorder=usage_recorder,
        )
        self.key_repository = key_repository
        self.search_client = search_client

    async def execute(self, command: CreateChatCompletionsCommand) -> CreateChatCompletionsUseCaseResult:
        authenticated_user = command.authenticated_user

        result = await self._resolve_router(authenticated_user=authenticated_user, model_name_or_alias=command.model)
        match result:
            case Router() as router:
                pass
            case error:
                return error

        payload, search_arguments = command.payload.pop_search_tool()
        search_results: list[Search] | None = None

        if self.search_client is not None and search_arguments is not None:
            try:
                search_args = SearchArgs(**search_arguments)
            except ValidationError as e:
                return SearchArgsValidationError(errors=e.errors())

            search_results = []
            query = payload.get_last_user_query()
            key = await self.key_repository.upsert_key(
                user_id=authenticated_user.id,
                name=SEARCH_KEY_NAME,
                expire=datetime.now(tz=UTC) + SEARCH_KEY_TTL,
            )
            # a user that vanished between authentication and here leaves the request ungrounded rather than failing it
            if query and isinstance(key, Key):
                match await self.search_client.search(key_value=key.value, query=query, args=search_args):
                    case Searches() as searches:
                        search_results = searches.data
                        if searches.data:
                            payload = payload.with_last_message_content(content=searches.build_grounded_prompt(query=query))
                    case SearchStatusCodeError() as error:
                        return error
                    case SearchUnreachableError():
                        pass

        prompt_tokens = self.model_tokenizer.compute_tokens(texts=payload.get_prompts())

        result = await self._check_rate_limits(authenticated_user=authenticated_user, router=router, prompt_tokens=prompt_tokens)
        match result:
            case RouterRateLimitState() as rate_limit_state:
                pass
            case error:
                return error

        if payload.stream:
            provider = await self._select_provider(router=router)
            request = ProviderRequest(endpoint=self.ENDPOINT, payload=payload)

            match await self.provider_client.forward_stream(provider=provider, request=request):
                case AsyncGenerator() as chunks:
                    pass
                case error:
                    return error

            return CreateChatCompletionsStreamUseCaseSuccess(
                chunks=self._forward_stream(
                    router=router,
                    provider=provider,
                    chunks=chunks,
                    prompt_tokens=prompt_tokens,
                    search_results=search_results,
                ),
                headers=rate_limit_state.build_limit_headers,
            )

        result = await self._send_request(router=router, prompt_tokens=prompt_tokens, payload=payload)
        match result:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return error

        provider_response.data.search_results = search_results

        return CreateChatCompletionsUseCaseSuccess(data=provider_response.data, headers=rate_limit_state.build_limit_headers)

    async def _forward_stream(
        self,
        router: Router,
        provider: Provider,
        chunks: AsyncGenerator[ProviderStreamChunk],
        prompt_tokens: int,
        search_results: list[Search] | None,
    ) -> AsyncGenerator[ProviderStreamChunk]:
        inflight_is_incremented = await self.provider_metrics_logger.increment_inflight(provider_id=provider.id)

        start_time = time.perf_counter()
        buffer: list[dict] = []
        ttft: int | None = None
        latency: int | None = None
        usage_is_sent = False

        try:
            async for chunk in chunks:
                if chunk.status_code // 100 != 2:
                    yield chunk
                    return

                parsed_chunk = ChatCompletionChunk.parse_chunk(chunk=chunk.content)

                if parsed_chunk == "[DONE]":
                    latency = self._elapsed_ms(start_time=start_time)
                    yield ProviderStreamChunk(
                        content=self._build_usage_event(
                            router=router,
                            provider=provider,
                            buffer=buffer,
                            prompt_tokens=prompt_tokens,
                            latency=latency,
                            search_results=search_results,
                        ),
                        status_code=chunk.status_code,
                    )
                    usage_is_sent = True
                    yield ProviderStreamChunk(content=f"{chunk.content}\n\n", status_code=chunk.status_code)
                    continue

                if parsed_chunk is not None:
                    buffer.append(parsed_chunk)
                    if ttft is None and ChatCompletionChunk.extract_chunk_content(chunk=parsed_chunk):
                        ttft = self._elapsed_ms(start_time=start_time)

                yield ProviderStreamChunk(content=f"{chunk.content}\n\n", status_code=chunk.status_code)

            if not usage_is_sent:
                latency = self._elapsed_ms(start_time=start_time)
                yield ProviderStreamChunk(
                    content=self._build_usage_event(
                        router=router,
                        provider=provider,
                        buffer=buffer,
                        prompt_tokens=prompt_tokens,
                        latency=latency,
                        search_results=search_results,
                    ),
                    status_code=200,
                )

            await self.provider_metrics_logger.log_metric(provider_id=provider.id, metric=Metric.LATENCY, value=latency)
            if ttft is not None:
                await self.provider_metrics_logger.log_metric(provider_id=provider.id, metric=Metric.TTFT, value=ttft)
        finally:
            if inflight_is_incremented:
                await self.provider_metrics_logger.decrement_inflight(provider_id=provider.id)

    def _build_usage_event(
        self,
        router: Router,
        provider: Provider,
        buffer: list[dict],
        prompt_tokens: int,
        latency: int,
        search_results: list[Search] | None,
    ) -> str:
        completions = [content for chunk in buffer if (content := ChatCompletionChunk.extract_chunk_content(chunk=chunk))]
        completion_tokens = self.model_tokenizer.compute_tokens(texts=completions)
        usage = self._build_usage(
            provider=provider,
            router=router,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency=latency,
        )
        request_id = buffer[0].get("id") if buffer else None
        request_id = request_id or f"request-{uuid4().hex}"

        self.usage_recorder.record_usage(request_id=request_id, usage=usage)

        usage_chunk = ChatCompletionChunk.build_usage_chunk(
            last_chunk=buffer[-1] if buffer else {},
            request_id=request_id,
            model=router.name,
            usage=usage,
        )
        if search_results is not None:
            usage_chunk["search_results"] = [result.model_dump(mode="json") for result in search_results]

        return f"data: {dumps(usage_chunk)}\n\n"

    @staticmethod
    def _elapsed_ms(start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)
