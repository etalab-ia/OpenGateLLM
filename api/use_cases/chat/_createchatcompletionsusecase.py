from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from json import dumps
import time

from api.domain.chat.entities import ChatCompletion, ChatCompletionChunk, CreateChatCompletionsBody
from api.domain.model.errors import StatusCodeModelError
from api.domain.provider.entities import Provider, ProviderChunkResponse, ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.use_cases._providerrequestforwardingusecase import ForwardingCommand, ProviderRequestForwardingUseCase, ProviderRequestForwardingUseCaseError


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
    chunks: AsyncGenerator[ProviderChunkResponse]
    headers: dict[str, str]


type CreateChatCompletionsUseCaseResult = (
    CreateChatCompletionsUseCaseSuccess | CreateChatCompletionsStreamUseCaseSuccess | ProviderRequestForwardingUseCaseError
)


class CreateChatCompletionsUseCase(ProviderRequestForwardingUseCase[CreateChatCompletionsCommand, CreateChatCompletionsUseCaseResult]):
    ROUTER_TYPE = RouterType.TEXT_GENERATION
    ENDPOINT = ProviderEndpoint.CHAT_COMPLETIONS

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

        request_id = self._start_record_usage(command=command, router=router)

        if command.stream:
            provider = await self._select_provider(router=router)
            request = ProviderRequest(id=request_id, endpoint=self.ENDPOINT, payload=command.payload)

            match await self.provider_client.forward_stream(provider=provider, request=request):
                case AsyncGenerator() as chunks:
                    pass
                case error:
                    self.usage_recorder.fail_record(message=type(error).__name__)
                    self.usage_recorder.end_record()
                    return error

            return CreateChatCompletionsStreamUseCaseSuccess(
                chunks=self._format_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=prompt_tokens, request_id=request_id),
                headers=rate_limit_state.build_limit_headers,
            )

        try:
            result = await self._send_request(router=router, prompt_tokens=prompt_tokens, payload=command.payload, request_id=request_id)
            match result:
                case ProviderResponse() as provider_response:
                    pass
                case error:
                    self.usage_recorder.fail_record(message=type(error).__name__)
                    return error

            return self._build_success(command=command, response=provider_response, headers=rate_limit_state.build_limit_headers)
        finally:
            self.usage_recorder.end_record()

    async def _format_stream(
        self,
        router: Router,
        provider: Provider,
        chunks: AsyncGenerator[ProviderChunkResponse],
        prompt_tokens: int,
        request_id: str,
    ) -> AsyncGenerator[ProviderChunkResponse]:
        start_time = time.perf_counter()
        buffer: list[dict] = []
        first_token_at: datetime | None = None

        try:
            async with self._inflight(provider=provider):
                async for chunk in chunks:
                    if chunk.status_code // 100 != 2:
                        self.usage_recorder.fail_record(message=StatusCodeModelError.__name__)
                        yield chunk
                        return

                    parsed_chunk = ChatCompletionChunk.parse_chunk(chunk=chunk.content)

                    if parsed_chunk == "[DONE]":
                        break

                    if parsed_chunk is None:
                        yield ProviderChunkResponse(content=f"{chunk.content}\n\n", status_code=chunk.status_code)
                        continue

                    buffer.append(parsed_chunk)
                    if first_token_at is None and ChatCompletionChunk.extract_chunk_content(chunk=parsed_chunk):
                        first_token_at = datetime.now(tz=UTC)

                    relayed = {**parsed_chunk, "model": router.name, "id": request_id}
                    yield ProviderChunkResponse(content=f"data: {dumps(relayed)}\n\n", status_code=chunk.status_code)

                latency = self._elapsed(start_time=start_time)
                yield ProviderChunkResponse(
                    content=self._build_usage_event(
                        router=router,
                        provider=provider,
                        buffer=buffer,
                        prompt_tokens=prompt_tokens,
                        latency=latency,
                        request_id=request_id,
                        first_token_at=first_token_at,
                    ),
                    status_code=200,
                )
                yield ProviderChunkResponse(content="data: [DONE]\n\n", status_code=200)
        finally:
            self.usage_recorder.end_record()

    def _build_usage_event(
        self,
        router: Router,
        provider: Provider,
        buffer: list[dict],
        prompt_tokens: int,
        latency: float,
        request_id: str,
        first_token_at: datetime | None,
    ) -> str:
        completions = [content for chunk in buffer if (content := ChatCompletionChunk.extract_chunk_content(chunk=chunk))]
        completion_tokens = self.model_tokenizer.compute_tokens(texts=completions)
        usage = self._build_usage(provider=provider, router=router, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, latency=latency)
        self.usage_context.record_usage(usage=usage)
        self.usage_recorder.update_record(
            usage=usage,
            provider_id=provider.id,
            provider_model_name=provider.model_name,
            first_token_at=first_token_at,
        )

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
