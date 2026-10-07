import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from api.domain.key.entities import Key
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderChunkResponse
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.usage import UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext, RequestLogMiddleware, StreamingResponseWithStatusCode, UsageRecorder
from api.infrastructure.fastapi._usagerecorder import _pending_saves
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.chat import _as_stream_chunks
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory
from api.use_cases.chat import CreateChatCompletionsUseCase

DATA_LINE = 'data: {"id": "chat-1", "object": "chat.completion.chunk", "created": 1, "model": "provider-internal", "choices": [{"index": 0, "delta": {"content": "Hello"}}]}'  # noqa: E501
USER_ID = 42
# spec_version 2.3 is what uvicorn advertises, and it is what makes StreamingResponse watch for the disconnect in a
# task group of its own — the shape the cancellation actually travels through in production
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
def usage_recorder(mock_usage_repository) -> UsageRecorder:
    return UsageRecorder.open(
        usage_repository=mock_usage_repository,
        request_id="req-123",
        endpoint="/v1/chat/completions",
        user=_authenticated_user(),
        key=Key(id=7, name="my-key", user_id=USER_ID, value="sk-x", expires=None, created=datetime.now(tz=UTC)),
    )


@pytest.fixture
def use_case(usage_recorder) -> CreateChatCompletionsUseCase:
    tokenizer = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    impacts = create_autospec(ModelEnvironmentalImpactsComputer, instance=True, spec_set=True)
    impacts.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)

    return CreateChatCompletionsUseCase(
        model_environmental_impacts_computer=impacts,
        model_tokenizer=tokenizer,
        provider_client=create_autospec(ProviderClient, instance=True, spec_set=True),
        provider_load_balancer=create_autospec(ProviderLoadBalancer, instance=True, spec_set=True),
        provider_metrics_logger=create_autospec(ProviderMetricsLogger, instance=True, spec_set=True),
        provider_repository=create_autospec(ProviderRepository, instance=True, spec_set=True),
        router_rate_limiter=create_autospec(RouterRateLimiter, instance=True, spec_set=True),
        router_repository=create_autospec(RouterRepository, instance=True, spec_set=True),
        usage_context=usage_recorder,
    )


def _authenticated_user() -> AuthenticatedUserView:
    return AuthenticatedUserView(id=USER_ID, email="alice@example.com", name="Alice", organization_id=1, permissions=[], limits=[], expires=None)


def _provider_stream() -> AsyncGenerator[ProviderChunkResponse]:
    async def stream() -> AsyncGenerator[ProviderChunkResponse]:
        while True:  # the provider keeps talking as long as someone reads
            yield ProviderChunkResponse(content=DATA_LINE, status_code=200)

    return stream()


def _streaming_app(use_case, router, provider):
    """The layers production stacks: the endpoint's own SSE adapter over the use case's stream."""

    async def app(scope, receive, send) -> None:
        response = StreamingResponseWithStatusCode(
            content=_as_stream_chunks(
                use_case._format_stream(
                    authenticated_user=_authenticated_user(),
                    router=router,
                    provider=provider,
                    chunks=_provider_stream(),
                    prompt_tokens=1,
                    request_id="req-123",
                )
            ),
            media_type="text/event-stream",
        )
        await response(scope, receive, send)

    return app


async def _receive() -> dict:
    # a real server blocks here until the client says something; returning at once would starve the event loop
    await asyncio.Event().wait()
    raise AssertionError("unreachable")


@pytest.mark.asyncio(loop_scope="function")
class TestUsageRecordedOnClientDisconnect:
    async def test_should_save_the_usage_record_when_the_client_disconnects(self, use_case, usage_recorder, mock_usage_repository, router, provider):
        """Starlette cancels the request scope on a disconnect. The chain closes top-down inside the request task, so
        the tokens already delivered are on the record by the time RequestLogMiddleware closes it."""
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
        await asyncio.gather(*tuple(_pending_saves))

        # Assert
        mock_usage_repository.save_record.assert_awaited_once_with(usage_recorder.record)
        assert usage_recorder.record.usage.completion_tokens == 1, "the chunk the client already received must be billed"
        assert usage_recorder.record.status == 200, "the stream had already answered 200 when the client left"

    async def test_should_save_the_usage_record_when_releasing_the_provider_fails(
        self, use_case, usage_recorder, mock_usage_repository, router, provider
    ):
        """The Redis call releasing the inflight counter raises as soon as it suspends under a cancelled scope.
        Observed in production: without a guard, no usage row is written at all."""
        # Arrange
        request_context.set(RequestContext(id="req-123", user=_authenticated_user(), usage_recorder=usage_recorder))
        use_case.provider_metrics_logger.increment_inflight.return_value = True
        use_case.provider_metrics_logger.decrement_inflight.side_effect = asyncio.CancelledError()
        middleware = RequestLogMiddleware(_streaming_app(use_case, router, provider))

        async def slow_client(message: dict) -> None:
            await asyncio.sleep(1)

        task = asyncio.create_task(middleware(SCOPE, _receive, slow_client))
        await asyncio.sleep(0.05)

        # Act
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.gather(*tuple(_pending_saves))

        # Assert
        mock_usage_repository.save_record.assert_awaited_once_with(usage_recorder.record)
        assert usage_recorder.record.usage.completion_tokens == 1
