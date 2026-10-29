import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import create_autospec

from fastapi import FastAPI, Request
import pytest

from api.domain.chat.entities import CreateChatCompletionsBody
from api.domain.key.entities import Key
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderConcurrencyLimiter, ProviderRepository, ProviderReservation
from api.domain.provider.entities import ProviderChunkResponse
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext, RequestLogMiddleware, RequestTracer, StreamingResponseWithStatusCode, UsageRecorder
from api.infrastructure.fastapi.decorators import CLIENT_CLOSED_REQUEST, cancel_on_disconnect
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.chat import _as_stream_chunks
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, KeyFactory, ProviderFactory, RouterFactory
from api.use_cases.chat import CreateChatCompletionsCommand, CreateChatCompletionsUseCase

DATA_LINE = 'data: {"id": "chat-1", "object": "chat.completion.chunk", "created": 1, "model": "provider-internal", "choices": [{"index": 0, "delta": {"content": "Hello"}}]}'  # noqa: E501
USER_ID = 42
SCOPE = {
    "type": "http",
    "asgi": {"version": "3.0", "spec_version": "2.3"},
    "method": "POST",
    "path": "/v1/chat/completions",
    "path_params": {},
    "client": ("10.0.0.1", 42564),
}


@pytest.fixture
def provider():
    return ProviderFactory(id=7, router_id=1)


@pytest.fixture
def router():
    return RouterFactory(id=1, name="chat-router", type=RouterType.TEXT_GENERATION, providers=1)


@pytest.fixture
def mock_usage_repository():
    return create_autospec(UsageRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_tracer():
    return create_autospec(RequestTracer, instance=True, spec_set=True)


@pytest.fixture
def usage_recorder(mock_tracer) -> UsageRecorder:
    return UsageRecorder.open(
        tracer=mock_tracer,
        request_id="req-123",
        endpoint="/v1/chat/completions",
        user=_authenticated_user(),
        key=Key(id=7, name="my-key", user_id=USER_ID, value="sk-x", expires=None, created=datetime.now(tz=UTC)),
    )


@pytest.fixture
def use_case(usage_recorder, mock_usage_repository) -> CreateChatCompletionsUseCase:
    tokenizer = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    impacts = create_autospec(ModelEnvironmentalImpactsComputer, instance=True, spec_set=True)
    impacts.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)

    return CreateChatCompletionsUseCase(
        model_environmental_impacts_computer=impacts,
        model_tokenizer=tokenizer,
        provider_client=create_autospec(ProviderClient, instance=True, spec_set=True),
        provider_concurrency_limiter=create_autospec(ProviderConcurrencyLimiter, instance=True, spec_set=True),
        provider_repository=create_autospec(ProviderRepository, instance=True, spec_set=True),
        router_rate_limiter=create_autospec(RouterRateLimiter, instance=True, spec_set=True),
        router_repository=create_autospec(RouterRepository, instance=True, spec_set=True),
        usage_context=usage_recorder,
        usage_repository=mock_usage_repository,
    )


def _authenticated_user() -> AuthenticatedUserView:
    return AuthenticatedUserView(id=USER_ID, email="alice@example.com", name="Alice", organization_id=1, permissions=[], limits=[], expires=None)


def _provider_stream() -> AsyncGenerator[ProviderChunkResponse]:
    async def stream() -> AsyncGenerator[ProviderChunkResponse]:
        while True:  # the provider keeps talking as long as someone reads
            yield ProviderChunkResponse(content=DATA_LINE, status_code=200)

    return stream()


def _streaming_app(use_case, router, provider):
    async def app(scope, receive, send) -> None:
        response = StreamingResponseWithStatusCode(
            content=_as_stream_chunks(
                use_case._forward_stream_to_client(
                    authenticated_user=_authenticated_user(),
                    router=router,
                    reservation=ProviderReservation(provider=provider, request_id="req-123"),
                    provider_chunks=_provider_stream(),
                    estimated_prompt_tokens=1,
                    request_id="req-123",
                )
            ),
            media_type="text/event-stream",
        )
        await response(scope, receive, send)

    return app


def _non_streaming_app(use_case, command):
    app = FastAPI()

    @app.post("/v1/chat/completions")
    @cancel_on_disconnect
    async def create_chat_completions(request: Request):
        return await use_case.execute(command)

    return app


async def _receive() -> dict:
    await asyncio.Event().wait()
    raise AssertionError("unreachable")


@pytest.mark.asyncio(loop_scope="function")
class TestUsageRecordedOnClientDisconnect:
    async def test_should_save_the_usage_record_when_the_client_disconnects(
        self, use_case, usage_recorder, mock_usage_repository, mock_tracer, router, provider
    ):
        # Arrange: a slow client, so the chain sits parked on its yields when the disconnect lands
        request_context.set(RequestContext(id="req-123", user=_authenticated_user(), usage_recorder=usage_recorder))
        middleware = RequestLogMiddleware(_streaming_app(use_case, router, provider))

        async def slow_client(message: dict) -> None:
            await asyncio.sleep(1)

        task = asyncio.create_task(middleware(SCOPE, _receive, slow_client))
        await asyncio.sleep(0.05)

        # Act
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # Assert
        [saved] = [call.kwargs["record"] for call in mock_usage_repository.save_record.call_args_list]
        assert saved.usage.completion_tokens == 1, "the chunk the client already received must be billed"
        mock_tracer.end.assert_called_once_with(usage_recorder.record)
        assert usage_recorder.record.status == 200, "the stream had already answered 200 when the client left"

    async def test_should_save_the_usage_record_when_releasing_the_provider_fails(
        self, use_case, usage_recorder, mock_usage_repository, router, provider
    ):
        # Arrange
        request_context.set(RequestContext(id="req-123", user=_authenticated_user(), usage_recorder=usage_recorder))
        use_case.provider_concurrency_limiter.release.side_effect = asyncio.CancelledError()
        middleware = RequestLogMiddleware(_streaming_app(use_case, router, provider))

        async def slow_client(message: dict) -> None:
            await asyncio.sleep(1)

        task = asyncio.create_task(middleware(SCOPE, _receive, slow_client))
        await asyncio.sleep(0.05)

        # Act
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # Assert
        [saved] = [call.kwargs["record"] for call in mock_usage_repository.save_record.call_args_list]
        assert saved.usage.completion_tokens == 1

    async def test_should_release_the_reservation_when_the_client_disconnects_before_the_first_chunk(self, use_case, router, provider):
        """Below ASGI 2.4, Starlette schedules stream_response in a task and listens for the disconnect in the current one.
        A client already gone cancels the scope before that task has run, but anyio only cancels a task once it has started:
        the chain is entered, so its finally blocks run and the reservation is released."""

        # Arrange
        app = _streaming_app(use_case, router, provider)
        scope = {"type": "http", "asgi": {"spec_version": "2.0"}}

        async def receive() -> dict:
            return {"type": "http.disconnect"}

        async def slow_send(message: dict) -> None:
            await asyncio.sleep(1)

        # Act
        await app(scope, receive, slow_send)

        # Assert
        use_case.provider_concurrency_limiter.release.assert_awaited_once_with(
            reservation=ProviderReservation(provider=provider, request_id="req-123")
        )

    async def test_should_answer_499_without_saving_usage_when_a_non_streamed_client_disconnects(
        self, use_case, usage_recorder, mock_usage_repository, mock_tracer, router, provider
    ):
        # Arrange: the provider never answers, the client leaves while waiting for it
        request_context.set(RequestContext(id="req-123", user=_authenticated_user(), usage_recorder=usage_recorder))
        reservation = ProviderReservation(provider=provider, request_id="req-123")
        use_case.router_repository.get_router_by_name_or_alias.return_value = router
        use_case.provider_repository.get_all_providers_of_router.return_value = [provider]
        use_case.provider_concurrency_limiter.reserve.return_value = reservation
        provider_called = asyncio.Event()

        async def provider_never_answering(provider, request):
            provider_called.set()
            await asyncio.Event().wait()

        use_case.provider_client.forward.side_effect = provider_never_answering
        command = CreateChatCompletionsCommand(
            payload=CreateChatCompletionsBody(model=router.name, messages=[{"role": "user", "content": "hello"}], stream=False),
            authenticated_user=AuthenticatedUserFactory(id=1, admin=True),
            authenticated_key=KeyFactory(),
        )
        middleware = RequestLogMiddleware(_non_streaming_app(use_case, command))
        messages = iter([{"type": "http.request", "body": b"", "more_body": False}])

        async def receive() -> dict:
            if (message := next(messages, None)) is not None:
                return message
            await provider_called.wait()
            return {"type": "http.disconnect"}

        sent = []

        async def send(message: dict) -> None:
            sent.append(message)

        scope = {**SCOPE, "http_version": "1.1", "raw_path": b"/v1/chat/completions", "root_path": "", "scheme": "http", "query_string": b"", "headers": [], "server": ("test", 80)}  # fmt: off

        # Act
        await middleware(scope, receive, send)

        # Assert
        assert sent[0]["status"] == CLIENT_CLOSED_REQUEST
        mock_usage_repository.save_record.assert_not_called()
        use_case.provider_concurrency_limiter.release.assert_awaited_once_with(reservation=reservation)
        mock_tracer.end.assert_called_once_with(usage_recorder.record)
        assert usage_recorder.record.status == CLIENT_CLOSED_REQUEST, "the trace must end with the status the client was answered"
