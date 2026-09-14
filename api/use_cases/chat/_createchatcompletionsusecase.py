from collections.abc import AsyncGenerator
from dataclasses import dataclass
from json import dumps
import time
from uuid import uuid4

from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk, CreateChatCompletionsBody
from api.domain.provider.entities import Metric, Provider, ProviderRequest, ProviderResponse, ProviderStreamChunk
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.use_cases._providerrequestforwardingusecase import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseError
from api.utils.variables import EndpointRoute


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
    CreateChatCompletionsUseCaseSuccess | CreateChatCompletionsStreamUseCaseSuccess | ProviderRequestForwardingUseCaseError
)


class CreateChatCompletionsUseCase(ProviderRequestForwardingUseCase[CreateChatCompletionsCommand, CreateChatCompletionsUseCaseResult]):
    ROUTER_TYPE = RouterType.TEXT_GENERATION
    ENDPOINT = EndpointRoute.CHAT_COMPLETIONS

    async def execute(self, command: CreateChatCompletionsCommand) -> CreateChatCompletionsUseCaseResult:
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

        if command.stream:
            provider = await self._select_provider(router=router)
            request = ProviderRequest(endpoint=self.ENDPOINT, payload=command.payload)

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
                ),
                headers=rate_limit_state.build_limit_headers,
            )

        result = await self._send_request(router=router, prompt_tokens=prompt_tokens, payload=command.payload)
        match result:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return error

        return self._build_success(command=command, response=provider_response, headers=rate_limit_state.build_limit_headers)

    async def _forward_stream(
        self,
        router: Router,
        provider: Provider,
        chunks: AsyncGenerator[ProviderStreamChunk],
        prompt_tokens: int,
    ) -> AsyncGenerator[ProviderStreamChunk]:
        start_time = time.perf_counter()
        buffer: list[dict] = []
        ttft: int | None = None
        latency: int | None = None
        usage_is_sent = False

        async with self._inflight(provider=provider):
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
                        ),
                        status_code=chunk.status_code,
                    )
                    usage_is_sent = True
                    yield ProviderStreamChunk(content=f"{chunk.content}\n\n", status_code=chunk.status_code)
                    break

                if parsed_chunk is None:
                    yield ProviderStreamChunk(content=f"{chunk.content}\n\n", status_code=chunk.status_code)
                    continue

                buffer.append(parsed_chunk)
                if ttft is None and ChatCompletionChunk.extract_chunk_content(chunk=parsed_chunk):
                    ttft = self._elapsed_ms(start_time=start_time)

                relayed = {**parsed_chunk, "model": router.name}
                yield ProviderStreamChunk(content=f"data: {dumps(relayed)}\n\n", status_code=chunk.status_code)

            if not usage_is_sent:
                latency = self._elapsed_ms(start_time=start_time)
                yield ProviderStreamChunk(
                    content=self._build_usage_event(
                        router=router,
                        provider=provider,
                        buffer=buffer,
                        prompt_tokens=prompt_tokens,
                        latency=latency,
                    ),
                    status_code=200,
                )

            await self.provider_metrics_logger.log_metric(provider_id=provider.id, metric=Metric.LATENCY, value=latency)
            if ttft is not None:
                await self.provider_metrics_logger.log_metric(provider_id=provider.id, metric=Metric.TTFT, value=ttft)

    def _build_usage_event(
        self,
        router: Router,
        provider: Provider,
        buffer: list[dict],
        prompt_tokens: int,
        latency: int,
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
        return f"data: {dumps(usage_chunk)}\n\n"

    def _build_success(
        self,
        command: CreateChatCompletionsCommand,
        response: ProviderResponse,
        headers: dict[str, str],
    ) -> CreateChatCompletionsUseCaseSuccess:
        return CreateChatCompletionsUseCaseSuccess(data=response.data, headers=headers)
