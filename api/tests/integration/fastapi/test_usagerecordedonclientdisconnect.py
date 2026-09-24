import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
import gc
from unittest.mock import create_autospec

import pytest

from api.domain.key.entities import Key
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderChunkResponse
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.usage import UsageContext, UsageRecorder
from api.domain.usage.entities import EnvironmentalImpacts
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi import RequestContext
from api.infrastructure.fastapi._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from api.infrastructure.fastapi.decorators import _wrap_streaming_response, set_usage_from_context
from api.infrastructure.fastapi.dependencies import request_context
from api.infrastructure.fastapi.endpoints.chat import _as_stream_chunks
from api.infrastructure.postgres.models import Usage as UsageRow
from api.tests.unit.use_case.factories import ProviderFactory, RouterFactory
from api.use_cases.chat import CreateChatCompletionsUseCase

DATA_LINE = 'data: {"id": "chat-1", "object": "chat.completion.chunk", "created": 1, "model": "provider-internal", "choices": [{"index": 0, "delta": {"content": "Hello"}}]}'  # noqa: E501
USER_ID = 42


@pytest.fixture
def provider():
    return ProviderFactory(id=7, router_id=1)


@pytest.fixture
def router():
    return RouterFactory(id=1, name="chat-router", type=RouterType.TEXT_GENERATION, providers=1)


@pytest.fixture
def use_case() -> CreateChatCompletionsUseCase:
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
        usage_context=create_autospec(UsageContext, instance=True, spec_set=True),
        usage_recorder=create_autospec(UsageRecorder, instance=True, spec_set=True),
    )


def _request_context() -> RequestContext:
    now = datetime.now(tz=UTC)

    return RequestContext(
        endpoint="/v1/chat/completions",
        key=Key(id=7, name="my-key", user_id=USER_ID, value="sk-x", expires=None, created=now),
        user=AuthenticatedUserView(
            id=USER_ID, email="alice@example.com", name="Alice", organization_id=1, budget=1.0, permissions=[], limits=[], expires=None
        ),
    )


def _provider_stream() -> AsyncGenerator[ProviderChunkResponse]:
    async def stream() -> AsyncGenerator[ProviderChunkResponse]:
        while True:  # the provider keeps talking as long as someone reads
            yield ProviderChunkResponse(content=DATA_LINE, status_code=200)

    return stream()


def _assemble(use_case, router, provider, outcome: list[str]) -> StreamingResponseWithStatusCode:
    """Stack the layers exactly as `@hooks` and the chat endpoint do — `_as_stream_chunks` is the endpoint's own adapter."""
    inner = StreamingResponseWithStatusCode(
        content=_as_stream_chunks(
            use_case._format_stream(
                router=router,
                provider=provider,
                chunks=_provider_stream(),
                prompt_tokens=1,
                request_id="req-123",
            )
        ),
        media_type="text/event-stream",
    )

    def record(usage: UsageRow) -> None:
        # the real mapper, so the test sees what production sees: it reads `request_context` and raises without it
        try:
            outcome.append(f"user_id={set_usage_from_context(usage=usage).user_id}")
        except Exception as error:
            outcome.append(type(error).__name__)

    return _wrap_streaming_response(response=inner, usage=UsageRow(endpoint="/v1/chat/completions"), record=record)


@pytest.mark.asyncio
class TestUsageRecordedOnClientDisconnect:
    async def test_should_record_the_usage_row_when_the_client_disconnects(self, use_case, router, provider):
        # Arrange: a slow client, so the chain sits parked on its yields when the disconnect lands
        outcome: list[str] = []
        response = _assemble(use_case, router, provider, outcome)

        async def slow_client(message: dict) -> None:
            await asyncio.sleep(1)

        async def request_task(streamed: StreamingResponseWithStatusCode) -> None:
            # as the middleware does: the context belongs to the request task, not to whoever collects it later
            request_context.set(_request_context())
            await streamed.stream_response(slow_client)

        task = asyncio.create_task(request_task(response))
        await asyncio.sleep(0.05)

        # Act: the disconnect cancels the task Starlette runs stream_response in
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # give the collector its chance — the point is that the row is lost, not that it is late
        del task, response, request_task
        gc.collect()
        for _ in range(30):
            await asyncio.sleep(0.01)

        # Assert
        assert outcome == [f"user_id={USER_ID}"], (
            "the usage row was not built inside the request context: a client disconnecting mid-stream is never billed"
        )
