from collections.abc import AsyncGenerator
import json
from unittest.mock import AsyncMock, create_autospec

import pytest

from api.domain.chat.entities import ChatCompletion, CreateChatCompletionsBody
from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.model.errors import TooBusyModelError
from api.domain.provider import ProviderClient, ProviderLoadBalancer, ProviderMetricsLogger, ProviderRepository
from api.domain.provider.entities import ProviderResponse, ProviderStreamChunk, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.domain.role.entities import LimitType
from api.domain.router import RouterRateLimiter, RouterRepository
from api.domain.router.entities import RouterRateLimitState, RouterType
from api.domain.router.errors import RouterNotFoundError, RouterRateLimitExceededError
from api.domain.usage import UsageRecorder
from api.domain.usage.entities import EnvironmentalImpacts
from api.tests.unit.use_case.factories import AuthenticatedUserFactory, ProviderFactory, RouterFactory
from api.use_cases.chat import (
    CreateChatCompletionsCommand,
    CreateChatCompletionsStreamUseCaseSuccess,
    CreateChatCompletionsUseCase,
    CreateChatCompletionsUseCaseSuccess,
)
from api.utils.variables import EndpointRoute

MODEL_NAME = "chat-router"


@pytest.fixture
def mock_model_tokenizer():
    tokenizer = create_autospec(ModelTokenizer, instance=True, spec_set=True)
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    return tokenizer


@pytest.fixture
def mock_usage_recorder():
    return create_autospec(UsageRecorder, instance=True, spec_set=True)


@pytest.fixture
def router():
    return RouterFactory(id=1, name=MODEL_NAME, type=RouterType.TEXT_GENERATION, providers=1)


@pytest.fixture
def provider():
    return ProviderFactory(id=7, router_id=1)


@pytest.fixture
def admin_user():
    return AuthenticatedUserFactory(id=1, admin=True)


@pytest.fixture
def make_command(admin_user):
    def _make(*, stream: bool = False, tools: list[dict] | None = None, content: str = "hello"):
        return CreateChatCompletionsCommand(
            payload=CreateChatCompletionsBody(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": content}],
                stream=stream,
                tools=tools,
            ),
            authenticated_user=admin_user,
        )

    return _make


@pytest.fixture
def sample_completion():
    return ChatCompletion(
        id="chat-1",
        model=MODEL_NAME,
        object="chat.completion",
        created=0,
        choices=[{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi there"}}],
    )


@pytest.fixture
def use_case(mock_model_tokenizer, mock_usage_recorder) -> CreateChatCompletionsUseCase:
    return CreateChatCompletionsUseCase(
        model_environmental_impacts_computer=create_autospec(ModelEnvironmentalImpactsComputer, instance=True, spec_set=True),
        model_tokenizer=mock_model_tokenizer,
        provider_client=create_autospec(ProviderClient, instance=True, spec_set=True),
        provider_load_balancer=create_autospec(ProviderLoadBalancer, instance=True, spec_set=True),
        provider_metrics_logger=create_autospec(ProviderMetricsLogger, instance=True, spec_set=True),
        provider_repository=create_autospec(ProviderRepository, instance=True, spec_set=True),
        router_rate_limiter=create_autospec(RouterRateLimiter, instance=True, spec_set=True),
        router_repository=create_autospec(RouterRepository, instance=True, spec_set=True),
        usage_recorder=mock_usage_recorder,
    )


async def _chunk_stream(*contents: str, status_code: int = 200) -> AsyncGenerator[ProviderStreamChunk]:
    for content in contents:
        yield ProviderStreamChunk(content=content, status_code=status_code)


class TestCreateChatCompletionsUseCase:
    def test_should_use_text_generation_router_type(self):
        assert CreateChatCompletionsUseCase.ROUTER_TYPE == RouterType.TEXT_GENERATION

    def test_should_use_chat_completions_endpoint(self):
        assert CreateChatCompletionsUseCase.ENDPOINT == EndpointRoute.CHAT_COMPLETIONS


class TestCreateChatCompletionsUseCaseExecute:
    @pytest.fixture(autouse=True)
    def mock_collaborator_methods(self, use_case, router, sample_completion, provider):
        use_case._resolve_router = AsyncMock(return_value=router)
        use_case._check_rate_limits = AsyncMock(return_value=RouterRateLimitState.admin_rate_limit_state())
        use_case._send_request = AsyncMock(return_value=ProviderResponse(id=sample_completion.id, data=sample_completion))
        use_case._select_provider = AsyncMock(return_value=provider)
        use_case.provider_client.forward_stream = AsyncMock(return_value=_chunk_stream())

    @pytest.mark.asyncio
    async def test_should_call_parent_methods_and_return_success(self, use_case, make_command, admin_user, router, sample_completion):
        # Arrange
        command = make_command()
        rate_limit_state = RouterRateLimitState.admin_rate_limit_state()
        use_case._check_rate_limits.return_value = rate_limit_state

        # Act
        result = await use_case.execute(command=command)

        # Assert
        use_case._resolve_router.assert_awaited_once_with(authenticated_user=admin_user, model_name_or_alias=MODEL_NAME)
        use_case.model_tokenizer.compute_tokens.assert_called_once_with(texts=["hello"])
        use_case._check_rate_limits.assert_awaited_once_with(authenticated_user=admin_user, router=router, prompt_tokens=1)
        assert isinstance(result, CreateChatCompletionsUseCaseSuccess)
        assert result.data is sample_completion
        assert result.headers == rate_limit_state.build_limit_headers

    @pytest.mark.asyncio
    async def test_should_return_stream_success_without_consuming_the_stream_when_stream_is_requested(self, use_case, make_command):
        # Arrange
        command = make_command(stream=True)

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateChatCompletionsStreamUseCaseSuccess)
        use_case._send_request.assert_not_awaited()
        use_case.provider_metrics_logger.increment_inflight.assert_not_awaited()  # the generator is returned unconsumed
        forwarded_request = use_case.provider_client.forward_stream.call_args.kwargs["request"]
        assert forwarded_request.id.startswith("request-")

    @pytest.mark.asyncio
    async def test_should_return_the_error_when_the_router_cannot_be_resolved(self, use_case, make_command):
        # Arrange
        use_case._resolve_router.return_value = RouterNotFoundError(name=MODEL_NAME)

        # Act
        result = await use_case.execute(command=make_command())

        # Assert
        assert result == RouterNotFoundError(name=MODEL_NAME)
        use_case._check_rate_limits.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_the_error_when_the_rate_limit_is_exceeded(self, use_case, make_command):
        # Arrange
        error = RouterRateLimitExceededError(id=1, limit_type=LimitType.RPM, headers={})
        use_case._check_rate_limits.return_value = error

        # Act
        result = await use_case.execute(command=make_command())

        # Assert
        assert result is error
        use_case._send_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_the_error_when_the_request_fails(self, use_case, make_command):
        # Arrange
        error = TooBusyModelError(status_code=503, detail="provider busy")
        use_case._send_request.return_value = error

        # Act
        result = await use_case.execute(command=make_command())

        # Assert
        assert result is error

    @pytest.mark.asyncio
    async def test_should_return_the_error_when_the_provider_client_refuses_to_open_the_stream(self, use_case, make_command):
        # Arrange: forward_stream answers with a typed error instead of a generator
        error = ProviderAdapterValidationRequestError(provider_type=ProviderType.VLLM, errors=[{"msg": "invalid"}])
        use_case.provider_client.forward_stream.return_value = error

        # Act
        result = await use_case.execute(command=make_command(stream=True))

        # Assert
        assert result is error
        use_case.provider_metrics_logger.increment_inflight.assert_not_awaited()


class TestCreateChatCompletionsUseCaseForwardStream:
    @staticmethod
    async def _collect(chunks) -> list[ProviderStreamChunk]:
        return [chunk async for chunk in chunks]

    @pytest.mark.asyncio
    async def test_should_append_a_usage_chunk_before_the_done_chunk(self, use_case, router, provider, mock_usage_recorder):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream(
            'data: {"id": "chat-1", "choices": [{"delta": {"content": "hi"}}]}',
            "data: [DONE]",
        )

        # Act
        chunks = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=3))

        # Assert
        assert len(chunks) == 3
        assert chunks[0].content.startswith('data: {"id": "chat-1"')
        usage_chunk = json.loads(chunks[1].content.removeprefix("data: "))
        assert usage_chunk["id"] == "chat-1"
        assert usage_chunk["choices"] == []
        assert usage_chunk["usage"]["prompt_tokens"] == 3
        assert usage_chunk["usage"]["completion_tokens"] == 1
        assert chunks[2].content == "data: [DONE]\n\n"
        mock_usage_recorder.record_usage.assert_called_once()
        assert mock_usage_recorder.record_usage.call_args.kwargs["request_id"] == "chat-1"

    @pytest.mark.asyncio
    async def test_should_append_usage_and_done_when_the_provider_emits_no_chunks(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream()

        # Act
        collected = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        assert collected[-1].content == "data: [DONE]\n\n"
        assert collected[-1].status_code == 200

    @pytest.mark.asyncio
    async def test_should_append_a_usage_chunk_when_the_provider_closes_without_a_done_chunk(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream('data: {"id": "chat-1", "choices": [{"delta": {"content": "hi"}}]}')

        # Act
        chunks = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        assert len(chunks) == 3
        assert json.loads(chunks[1].content.removeprefix("data: "))["choices"] == []
        assert chunks[2].content == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_should_stop_the_stream_and_forward_the_error_when_the_provider_fails(self, use_case, router, provider):
        # Arrange
        chunks = _chunk_stream('{"detail": "Model is too busy"}', status_code=503)

        # Act
        chunks = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        assert len(chunks) == 1
        assert chunks[0].status_code == 503
        use_case.usage_recorder.record_usage.assert_not_called()
        use_case.provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=provider.id)

    @pytest.mark.asyncio
    async def test_should_relay_data_chunks_under_the_router_name(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream('data: {"id": "chat-1", "model": "provider-internal", "choices": [{"delta": {"content": "hi"}}]}', "data: [DONE]")

        # Act
        collected = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        relayed = json.loads(collected[0].content.removeprefix("data: "))
        assert relayed["model"] == router.name
        assert relayed["choices"] == [{"delta": {"content": "hi"}}]

    @pytest.mark.asyncio
    async def test_should_stop_at_the_terminator_and_emit_a_single_usage_chunk(self, use_case, router, provider, mock_usage_recorder):
        # Arrange: a provider that keeps talking after [DONE]
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream('data: {"id": "chat-1", "choices": []}', "data: [DONE]", "data: [DONE]")

        # Act
        collected = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        assert [chunk.content for chunk in collected].count("data: [DONE]\n\n") == 1
        mock_usage_recorder.record_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_relay_an_unparseable_line_untouched_and_keep_it_out_of_the_usage(self, use_case, router, provider):
        # Arrange: an SSE keep-alive comment, which carries no completion to count
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream(": keep-alive", 'data: {"id": "chat-1", "choices": [{"delta": {"content": "hi"}}]}', "data: [DONE]")

        # Act
        collected = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        assert collected[0].content == ": keep-alive\n\n"
        usage_chunk = json.loads(collected[2].content.removeprefix("data: "))
        assert usage_chunk["usage"]["completion_tokens"] == 1  # the comment never reached the buffer

    @pytest.mark.asyncio
    async def test_should_release_the_inflight_counter_when_the_consumer_abandons_the_stream(self, use_case, router, provider):
        # Arrange
        chunks = _chunk_stream('data: {"id": "chat-1", "choices": []}', "data: [DONE]")
        stream = use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1)

        # Act: read one chunk, then drop the generator without exhausting it
        await stream.__anext__()
        await stream.aclose()

        # Assert
        use_case.provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=provider.id)

    @pytest.mark.asyncio
    async def test_should_release_the_inflight_counter_when_the_stream_completes(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        use_case.provider_metrics_logger.increment_inflight.return_value = True
        chunks = _chunk_stream(
            'data: {"id": "chat-1", "choices": [{"delta": {"content": "hi"}}]}',
            "data: [DONE]",
        )

        # Act
        await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1))

        # Assert
        use_case.provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=provider.id)
