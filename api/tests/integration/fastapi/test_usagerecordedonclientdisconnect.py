import asyncio
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack
import gc
from unittest.mock import create_autospec

import pytest

from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider import ProviderClient, ProviderQoS, ProviderRepository
from api.domain.provider.entities import ProviderChunkResponse
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterType
from api.domain.usage import UsageContext, UsageRepository
from api.domain.usage.entities import EnvironmentalImpacts
from api.infrastructure.fastapi._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from api.infrastructure.fastapi.endpoints.chat import _as_stream_chunks
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases.chat import CreateChatCompletionsUseCase

DATA_LINE = 'data: {"id": "chat-1", "object": "chat.completion.chunk", "created": 1, "model": "provider-internal", "choices": [{"index": 0, "delta": {"content": "Hello"}}]}'  # noqa: E501


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
        provider_qos=create_autospec(ProviderQoS, instance=True, spec_set=True),
        provider_repository=create_autospec(ProviderRepository, instance=True, spec_set=True),
        router_rate_limiter=create_autospec(RouterRateLimiter, instance=True, spec_set=True),
        router_repository=create_autospec(RouterRepository, instance=True, spec_set=True),
        usage_context=create_autospec(UsageContext, instance=True, spec_set=True),
        usage_repository=create_autospec(UsageRepository, instance=True, spec_set=True),
    )


def _provider_stream() -> AsyncGenerator[ProviderChunkResponse]:
    async def stream() -> AsyncGenerator[ProviderChunkResponse]:
        while True:  # the provider keeps talking as long as someone reads
            yield ProviderChunkResponse(content=DATA_LINE, status_code=200)

    return stream()


def _assemble(use_case, router, provider) -> StreamingResponseWithStatusCode:
    """Stack the layers exactly as the chat endpoint does — `_as_stream_chunks` is the endpoint's own adapter."""
    return StreamingResponseWithStatusCode(
        content=_as_stream_chunks(
            use_case._format_stream(
                authenticated_user=AuthenticatedUserFactory(),
                router=router,
                provider=provider,
                reservation=AsyncExitStack(),
                chunks=_provider_stream(),
                prompt_tokens=1,
                request_id="req-123",
            )
        ),
        media_type="text/event-stream",
    )


@pytest.mark.asyncio
class TestUsageRecordedOnClientDisconnect:
    async def test_should_record_the_usage_row_when_closing_the_chain_is_cancelled(self, use_case, router, provider):
        """Starlette cancels the request scope on a disconnect, so the Redis call releasing the inflight counter raises
        as soon as it suspends. Observed in production: without a guard, no usage row is written at all."""
        # Arrange
        use_case.provider_metrics_logger.increment_inflight.return_value = True
        use_case.provider_metrics_logger.decrement_inflight.side_effect = asyncio.CancelledError()
        response = _assemble(use_case, router, provider)

        async def slow_client(message: dict) -> None:
            await asyncio.sleep(1)

        task = asyncio.create_task(response.stream_response(slow_client))
        await asyncio.sleep(0.05)

        # Act
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # Assert
        use_case.usage_repository.end_record.assert_called_once()

    async def test_should_record_the_usage_row_when_the_client_disconnects(self, use_case, router, provider):
        # Arrange: a slow client, so the chain sits parked on its yields when the disconnect lands
        response = _assemble(use_case, router, provider)

        async def slow_client(message: dict) -> None:
            await asyncio.sleep(1)

        async def request_task(streamed: StreamingResponseWithStatusCode) -> None:
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
        use_case.usage_repository.end_record.assert_called_once()
