from collections.abc import AsyncGenerator
import json
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from api.domain.chat.entities import ChatCompletion, CreateChatCompletionsBody
from api.domain.key.entities import Key
from api.domain.provider.entities import Metric, ProviderResponse, ProviderStreamChunk
from api.domain.router.entities import RouterRateLimitState, RouterType
from api.domain.search import SearchClient
from api.domain.search.entities import Chunk, Search, Searches, SearchMethod
from api.domain.search.errors import SearchArgsValidationError, SearchStatusCodeError, SearchUnreachableError
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
    tokenizer = MagicMock()
    tokenizer.compute_tokens.side_effect = lambda texts: len(texts)
    return tokenizer


@pytest.fixture
def mock_usage_recorder():
    return create_autospec(UsageRecorder, instance=True, spec_set=True)


@pytest.fixture
def mock_search_client():
    return create_autospec(SearchClient, instance=True, spec_set=True)


@pytest.fixture
def mock_key_repository():
    repository = AsyncMock()
    repository.upsert_key.return_value = Key(id=1, name="_system_search_tool", user_id=1, value="sk-search", expires=None, created=0)
    return repository


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
def use_case(mock_model_tokenizer, mock_usage_recorder, mock_key_repository, mock_search_client) -> CreateChatCompletionsUseCase:
    return CreateChatCompletionsUseCase(
        model_environmental_impacts_computer=MagicMock(),
        model_tokenizer=mock_model_tokenizer,
        provider_client=AsyncMock(),
        provider_load_balancer=AsyncMock(),
        provider_metrics_logger=AsyncMock(),
        provider_repository=AsyncMock(),
        router_rate_limiter=AsyncMock(),
        router_repository=AsyncMock(),
        usage_recorder=mock_usage_recorder,
        key_repository=mock_key_repository,
        search_client=mock_search_client,
    )


async def _chunk_stream(*contents: str, status_code: int = 200) -> AsyncGenerator[ProviderStreamChunk]:
    for content in contents:
        yield ProviderStreamChunk(content=content, status_code=status_code)


def _search_result(content: str) -> Search:
    return Search(method=SearchMethod.SEMANTIC, score=0.9, chunk=Chunk(id=1, collection_id=1, document_id=1, content=content))


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
        assert result.data.search_results is None
        assert result.headers == rate_limit_state.build_limit_headers

    @pytest.mark.asyncio
    async def test_should_not_call_search_when_no_search_tool_is_requested(self, use_case, make_command, mock_search_client):
        # Arrange
        command = make_command(tools=[{"type": "function"}])

        # Act
        await use_case.execute(command=command)

        # Assert
        mock_search_client.search.assert_not_awaited()
        use_case.key_repository.upsert_key.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_ground_the_last_message_and_expose_search_results_when_search_tool_is_requested(
        self, use_case, make_command, mock_search_client, mock_key_repository
    ):
        # Arrange
        search_result = _search_result(content="Paris is the capital of France.")
        mock_search_client.search.return_value = Searches(data=[search_result])
        command = make_command(tools=[{"type": "search", "limit": 5}], content="capital of France?")

        # Act
        result = await use_case.execute(command=command)

        # Assert
        mock_key_repository.upsert_key.assert_awaited_once()
        assert mock_key_repository.upsert_key.await_args.kwargs["name"] == "_system_search_tool"
        assert mock_search_client.search.await_args.kwargs["query"] == "capital of France?"
        assert mock_search_client.search.await_args.kwargs["args"].limit == 5

        forwarded_payload = use_case._send_request.await_args.kwargs["payload"]
        assert forwarded_payload.tools == []
        assert "Paris is the capital of France." in forwarded_payload.messages[-1]["content"]
        assert result.data.search_results == [search_result]

    @pytest.mark.asyncio
    async def test_should_leave_the_prompt_ungrounded_when_search_returns_nothing(self, use_case, make_command, mock_search_client):
        # Arrange
        mock_search_client.search.return_value = Searches(data=[])
        command = make_command(tools=[{"type": "search"}], content="capital of France?")

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert use_case._send_request.await_args.kwargs["payload"].messages[-1]["content"] == "capital of France?"
        assert result.data.search_results == []

    @pytest.mark.asyncio
    async def test_should_forward_the_request_when_the_search_service_is_unreachable(self, use_case, make_command, mock_search_client):
        # Arrange
        mock_search_client.search.return_value = SearchUnreachableError(detail="ConnectError")
        command = make_command(tools=[{"type": "search"}], content="capital of France?")

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, CreateChatCompletionsUseCaseSuccess)
        use_case._send_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_return_search_status_code_error_when_the_search_service_rejects_the_request(
        self, use_case, make_command, mock_search_client
    ):
        # Arrange
        mock_search_client.search.return_value = SearchStatusCodeError(status_code=403, detail="Forbidden")
        command = make_command(tools=[{"type": "search"}])

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert result == SearchStatusCodeError(status_code=403, detail="Forbidden")
        use_case._send_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_return_search_args_validation_error_when_search_tool_arguments_are_invalid(self, use_case, make_command):
        # Arrange
        command = make_command(tools=[{"type": "search", "method": "lexical", "score_threshold": 0.5}])

        # Act
        result = await use_case.execute(command=command)

        # Assert
        assert isinstance(result, SearchArgsValidationError)
        use_case._send_request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_skip_search_when_no_search_client_is_configured(self, use_case, make_command, mock_key_repository):
        # Arrange
        use_case.search_client = None
        command = make_command(tools=[{"type": "search"}])

        # Act
        result = await use_case.execute(command=command)

        # Assert
        mock_key_repository.upsert_key.assert_not_awaited()
        assert result.data.search_results is None

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
        chunks = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=3, search_results=None))

        # Assert
        assert len(chunks) == 3
        assert chunks[0].content.startswith('data: {"id": "chat-1"')
        usage_chunk = json.loads(chunks[1].content.removeprefix("data: "))
        assert usage_chunk["id"] == "chat-1"
        assert usage_chunk["choices"] == []
        assert usage_chunk["usage"]["prompt_tokens"] == 3
        assert usage_chunk["usage"]["completion_tokens"] == 1
        assert "search_results" not in usage_chunk
        assert chunks[2].content == "data: [DONE]\n\n"
        mock_usage_recorder.record_usage.assert_called_once()
        assert mock_usage_recorder.record_usage.call_args.kwargs["request_id"] == "chat-1"

    @pytest.mark.asyncio
    async def test_should_append_a_usage_chunk_when_the_provider_closes_without_a_done_chunk(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream('data: {"id": "chat-1", "choices": [{"delta": {"content": "hi"}}]}')

        # Act
        chunks = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1, search_results=None))

        # Assert
        assert len(chunks) == 2
        assert json.loads(chunks[1].content.removeprefix("data: "))["choices"] == []

    @pytest.mark.asyncio
    async def test_should_carry_search_results_on_the_usage_chunk(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        chunks = _chunk_stream('data: {"id": "chat-1", "choices": []}', "data: [DONE]")

        # Act
        chunks = await self._collect(
            use_case._forward_stream(
                router=router,
                provider=provider,
                chunks=chunks,
                prompt_tokens=1,
                search_results=[_search_result(content="grounding chunk")],
            )
        )

        # Assert
        usage_chunk = json.loads(chunks[1].content.removeprefix("data: "))
        assert usage_chunk["search_results"][0]["chunk"]["content"] == "grounding chunk"

    @pytest.mark.asyncio
    async def test_should_stop_the_stream_and_forward_the_error_when_the_provider_fails(self, use_case, router, provider):
        # Arrange
        chunks = _chunk_stream('{"detail": "Model is too busy"}', status_code=503)

        # Act
        chunks = await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1, search_results=None))

        # Assert
        assert len(chunks) == 1
        assert chunks[0].status_code == 503
        use_case.usage_recorder.record_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_release_the_inflight_counter_and_log_metrics(self, use_case, router, provider):
        # Arrange
        use_case.model_environmental_impacts_computer.compute.return_value = EnvironmentalImpacts(kWh=1.0, kgCO2eq=2.0)
        use_case.provider_metrics_logger.increment_inflight.return_value = True
        chunks = _chunk_stream(
            'data: {"id": "chat-1", "choices": [{"delta": {"content": "hi"}}]}',
            "data: [DONE]",
        )

        # Act
        await self._collect(use_case._forward_stream(router=router, provider=provider, chunks=chunks, prompt_tokens=1, search_results=None))

        # Assert
        use_case.provider_metrics_logger.decrement_inflight.assert_awaited_once_with(provider_id=provider.id)
        logged_metrics = {call.kwargs["metric"] for call in use_case.provider_metrics_logger.log_metric.await_args_list}
        assert logged_metrics == {Metric.LATENCY, Metric.TTFT}
