from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import dataclass

from api.domain.chat.entities import ChatCompletion, ChatCompletionStream, CreateChatCompletionsBody
from api.domain.provider.entities import Provider, ProviderChunkResponse, ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.domain.usage.entities import Usage
from api.domain.user.views import AuthenticatedUserView
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

        request_id = self.usage_context.get_request_id()

        if command.stream:
            provider = await self._select_provider(router=router)
            request = ProviderRequest(id=request_id, endpoint=self.ENDPOINT, payload=command.payload)

            match await self.provider_client.forward_stream(provider=provider, request=request):
                case AsyncGenerator() as chunks:
                    pass
                case error:
                    return error

            return CreateChatCompletionsStreamUseCaseSuccess(
                chunks=self._relay_stream(
                    authenticated_user=authenticated_user,
                    router=router,
                    provider=provider,
                    chunks=chunks,
                    prompt_tokens=prompt_tokens,
                    request_id=request_id,
                ),
                headers=rate_limit_state.build_limit_headers(prompt_tokens),
            )

        result = await self._send_request(
            authenticated_user=authenticated_user,
            router=router,
            prompt_tokens=prompt_tokens,
            payload=command.payload,
            request_id=request_id,
        )
        match result:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return error

        return CreateChatCompletionsUseCaseSuccess(data=provider_response.data, headers=rate_limit_state.build_limit_headers(prompt_tokens))

    async def _relay_stream(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        provider: Provider,
        chunks: AsyncGenerator[ProviderChunkResponse],
        prompt_tokens: int,
        request_id: str,
    ) -> AsyncGenerator[ProviderChunkResponse]:
        stream = ChatCompletionStream(model=router.name, request_id=request_id)
        completed = False

        async with self._inflight(provider=provider):
            async with aclosing(chunks):
                try:
                    async for chunk in chunks:
                        if chunk.status_code // 100 != 2:
                            yield chunk
                            return

                        line = stream.read(chunk.content)
                        if stream.is_done:
                            break
                        if line is not None:
                            yield ProviderChunkResponse(content=line, status_code=chunk.status_code)

                    completed = True
                finally:
                    if completed or stream.has_delivered:
                        usage = self._record_stream_usage(
                            authenticated_user=authenticated_user,
                            router=router,
                            provider=provider,
                            prompt_tokens=prompt_tokens,
                            stream=stream,
                            # a cut stream is billed on the tokenizer count, whether or not the client asked for running counts
                            provider_usage=stream.provider_usage if completed else None,
                        )

                if completed:
                    yield ProviderChunkResponse(content=stream.build_usage_line(usage=usage), status_code=200)
                    yield ProviderChunkResponse(content="data: [DONE]", status_code=200)

    def _record_stream_usage(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        provider: Provider,
        prompt_tokens: int,
        stream: ChatCompletionStream,
        provider_usage: Usage | None,
    ) -> Usage:
        latency = self.usage_context.elapsed_ms()
        prompt_tokens, completion_tokens, cached_tokens = self._count_tokens(
            prompt_tokens=prompt_tokens,
            completions=stream.completions,
            provider_usage=provider_usage,
        )
        usage = self._build_usage(
            provider=provider,
            router=router,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cached_tokens=cached_tokens,
            latency=latency,
        )
        ttft = self.usage_context.elapsed_ms(at=stream.first_token_at) if stream.first_token_at is not None else None
        self.usage_context.record_usage(usage=usage, latency=latency, ttft=ttft)
        self.usage_repository.save_record(record=self.usage_context.get_record())
        self._charge_rate_limits(authenticated_user=authenticated_user, router=router, usage=usage)

        return usage
