from collections.abc import AsyncGenerator
from contextlib import aclosing
from dataclasses import dataclass
from datetime import datetime

from api.domain.chat.entities import ChatCompletion, ChatCompletionStreamReader, CreateChatCompletionsBody
from api.domain.model.errors import StatusCodeModelError
from api.domain.provider import ProviderReservation, ProviderReservationRefused
from api.domain.provider.entities import Provider, ProviderChunkResponse, ProviderEndpoint, ProviderRequest, ProviderResponse
from api.domain.provider.errors import NoAvailableProviderError
from api.domain.router.entities import Router, RouterRateLimitState, RouterType
from api.domain.usage.entities import BilledTokens, Usage
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

        request_id = self.usage_context.get_request_id()

        if command.stream:
            providers = await self.provider_repository.get_all_providers_of_router(router_id=router.id)
            request = ProviderRequest(id=request_id, endpoint=self.ENDPOINT, payload=command.payload)

            result = await self._reserve_provider(
                providers=providers,
                strategy=router.load_balancing_strategy,
                retries_before_reject=router.qos_retries_before_reject,
                request_id=request_id,
            )
            match result:
                case ProviderReservation() as reservation:
                    provider = reservation.provider
                case ProviderReservationRefused() as reservation_refused:
                    return NoAvailableProviderError(
                        router_id=router.id,
                        retry_after=reservation_refused.retry_after(retries=router.qos_retries_before_reject),
                    )

            self.usage_context.record_provider(provider_id=provider.id, provider_model_name=provider.model_name)
            try:
                result = await self.provider_client.forward_stream(provider=provider, request=request)
            except BaseException:
                await self.provider_concurrency_limiter.release(reservation=reservation)
                raise

            match result:
                case AsyncGenerator() as provider_chunks:
                    pass
                case error:
                    await self.provider_concurrency_limiter.release(reservation=reservation)
                    return error

            # from here on the stream owns the reservation and releases it once consumed or closed
            return CreateChatCompletionsStreamUseCaseSuccess(
                chunks=self._forward_stream_to_client(
                    authenticated_user=authenticated_user,
                    router=router,
                    reservation=reservation,
                    provider_chunks=provider_chunks,
                    estimated_prompt_tokens=estimated_prompt_tokens,
                    request_id=request_id,
                ),
                headers=remaining_rate_limits.build_limit_headers(estimated_prompt_tokens),
            )

        result = await self._forward_request_to_provider(
            authenticated_user=authenticated_user,
            router=router,
            estimated_prompt_tokens=estimated_prompt_tokens,
            payload=command.payload,
            request_id=request_id,
        )
        match result:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return error

        return CreateChatCompletionsUseCaseSuccess(
            data=provider_response.data, headers=remaining_rate_limits.build_limit_headers(estimated_prompt_tokens)
        )

    async def _forward_stream_to_client(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        reservation: ProviderReservation,
        provider_chunks: AsyncGenerator[ProviderChunkResponse],
        estimated_prompt_tokens: int,
        request_id: str,
    ) -> AsyncGenerator[ProviderChunkResponse]:
        provider = reservation.provider
        stream_reader = ChatCompletionStreamReader(model=router.name, request_id=request_id)
        stream_was_fully_read = False

        try:
            async with aclosing(provider_chunks):
                try:
                    async for chunk in provider_chunks:
                        if chunk.status_code // 100 != 2:
                            # a stream that already answered 200 fails without any exception the middleware could see
                            self.usage_context.record_error(error=StatusCodeModelError.__name__)
                            yield chunk
                            return

                        line = stream_reader.read(chunk.content)
                        if stream_reader.has_reached_stream_end:
                            break
                        if line is not None:
                            yield ProviderChunkResponse(content=line, status_code=chunk.status_code)

                    stream_was_fully_read = True
                finally:
                    stream_was_cut_after_delivery = not stream_was_fully_read and stream_reader.has_delivered_chunks
                    if stream_was_cut_after_delivery:
                        billed_tokens_from_tokenizer = self._get_billed_tokens(
                            estimated_prompt_tokens=estimated_prompt_tokens,
                            completions=stream_reader.delivered_completions,
                            provider_usage=None,
                        )
                        self._bill_stream(
                            authenticated_user=authenticated_user,
                            router=router,
                            provider=provider,
                            billed_tokens=billed_tokens_from_tokenizer,
                            first_token_at=stream_reader.first_token_at,
                        )

                if stream_was_fully_read:
                    billed_tokens = self._get_billed_tokens(
                        estimated_prompt_tokens=estimated_prompt_tokens,
                        completions=stream_reader.delivered_completions,
                        provider_usage=stream_reader.provider_usage,
                    )
                    usage = self._bill_stream(
                        authenticated_user=authenticated_user,
                        router=router,
                        provider=provider,
                        billed_tokens=billed_tokens,
                        first_token_at=stream_reader.first_token_at,
                    )
                    yield ProviderChunkResponse(content=stream_reader.build_usage_line(usage=usage), status_code=200)
                    yield ProviderChunkResponse(content="data: [DONE]", status_code=200)
        finally:
            await self.provider_concurrency_limiter.release(reservation=reservation)

    def _bill_stream(
        self,
        authenticated_user: AuthenticatedUserView,
        router: Router,
        provider: Provider,
        billed_tokens: BilledTokens,
        first_token_at: datetime | None,
    ) -> Usage:
        latency = self.usage_context.elapsed_ms()
        usage = self._compute_usage(provider=provider, router=router, billed_tokens=billed_tokens, latency=latency)
        ttft = self.usage_context.elapsed_ms(at=first_token_at) if first_token_at is not None else None
        self._record_and_save_usage(usage=usage, latency=latency, ttft=ttft)
        self._charge_rate_limits(authenticated_user=authenticated_user, router=router, usage=usage)

        return usage
