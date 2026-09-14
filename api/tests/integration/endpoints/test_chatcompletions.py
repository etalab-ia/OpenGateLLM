import json
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_chat_completions_use_case_factory
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import HostingZone, ProviderType
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.role.entities import LimitType
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.schemas.models import ModelType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.conftest import override_global_context
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_chat_completions_responses, mock_chat_completions_stream
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.tests.integration.factories.vllm import VllmChatCompletionsResponseFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.CHAT_COMPLETIONS}"

DEFAULT_MODEL_NAME = "chat-router"
SAMPLE_VALIDATION_ERRORS = [{"type": "missing", "loc": ["messages"], "msg": "Field required", "input": {}}]

STREAM_LINES = [
    'data: {"id": "chatcmpl-1", "object": "chat.completion.chunk", "created": 1, "model": "provider-model", "choices": [{"index": 0, "delta": {"content": "Hello"}}]}',  # noqa: E501
    'data: {"id": "chatcmpl-1", "object": "chat.completion.chunk", "created": 1, "model": "provider-model", "choices": [{"index": 0, "delta": {"content": " world"}}]}',  # noqa: E501
    "data: [DONE]",
]


def _valid_body(**overrides) -> dict:
    body = {
        "model": DEFAULT_MODEL_NAME,
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateChatCompletions:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [0] * 10
        with override_global_context(redis_pool=test_redis_pool, _tokenizer=mock_tokenizer):
            yield

    async def _create_router(self, db_session):
        router = RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.TEXT_GENERATION,
            providers=1,
            providers__type=ProviderType.VLLM,
            providers__url=DEFAULT_PROVIDER_URL,
            providers__model_hosting_zone=HostingZone.FRA,  # pin to an ecologits-resolvable zone (chat always has completion tokens)
        )
        await db_session.flush()
        return router

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_chat_key", user=self.router_owner)
        await self._create_router(db_session)

        mock_chat_completions_responses(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmChatCompletionsResponseFactory(),
            status_code=VllmChatCompletionsResponseFactory._status_code,
        )

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {admin_key.token}"}, json=_valid_body())

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == DEFAULT_MODEL_NAME
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert data["usage"]["total_tokens"] == data["usage"]["prompt_tokens"] + data["usage"]["completion_tokens"]

    @respx.mock
    async def test_streamed_happy_path_appends_a_usage_chunk_before_done(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_chat_stream_key", user=self.router_owner)
        await self._create_router(db_session)

        mock_chat_completions_stream(respx_mock=respx, provider_type=ProviderType.VLLM, lines=STREAM_LINES)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            json=_valid_body(stream=True),
        )

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")

        events = [line for line in response.text.split("\n\n") if line.strip()]
        assert events[-1] == "data: [DONE]"

        usage_chunk = json.loads(events[-2].removeprefix("data: "))
        assert usage_chunk["choices"] == []
        assert usage_chunk["model"] == DEFAULT_MODEL_NAME
        assert usage_chunk["usage"]["completion_tokens"] > 0

    @respx.mock
    async def test_streamed_provider_error_is_forwarded_with_its_status(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_chat_stream_error_key", user=self.router_owner)
        await self._create_router(db_session)

        mock_chat_completions_stream(respx_mock=respx, provider_type=ProviderType.VLLM, lines=['{"detail": "bad request"}'], status_code=400)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            json=_valid_body(stream=True),
        )

        assert response.status_code == 400, response.text

    async def test_malformed_messages_returns_422_not_500(self, client: AsyncClient):
        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(messages=["Hello, how are you?"]),
        )

        assert response.status_code == 422, response.text

    @respx.mock
    async def test_null_stream_is_treated_as_non_streamed(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_chat_null_stream_key", user=self.router_owner)
        await self._create_router(db_session)

        mock_chat_completions_responses(
            respx_mock=respx,
            provider_type=ProviderType.VLLM,
            body=VllmChatCompletionsResponseFactory(),
            status_code=VllmChatCompletionsResponseFactory._status_code,
        )

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {admin_key.token}"}, json=_valid_body(stream=None))

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (RouterNotFoundError(name=DEFAULT_MODEL_NAME), 404, f"Model {DEFAULT_MODEL_NAME} not found."),
            (RouterHasNoProvidersError(id=1), 404, f"Model {DEFAULT_MODEL_NAME} not found."),
            (UserHasNoAccessToRouterError(id=1), 404, f"Model {DEFAULT_MODEL_NAME} not found."),
            (UserHasInsufficientBudgetError(), 400, "Insufficient budget."),
            (
                RouterHasWrongTypeError(id=1, actual_type=RouterType.TEXT_EMBEDDINGS_INFERENCE, expected_type=RouterType.TEXT_GENERATION),
                422,
                "Model has wrong type. Expected: text-generation. Actual: text-embeddings-inference.",
            ),
            (NoAvailableProviderError(router_id=1), 503, "Model is too busy, please try again later."),
            (TooBusyModelError(status_code=503, detail="provider busy"), 503, "Model is too busy, please try again later."),
            (RouterRateLimitExceededError(id=1, limit_type=LimitType.RPM, headers={}), 429, "Request limit per minute exceeded."),
            (StatusCodeModelError(status_code=400, detail="bad request"), 400, "bad request"),
            (UnknownModelError(status_code=500, detail="upstream failure"), 500, "upstream failure"),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_chat_completions_use_case_factory] = lambda: mock_use_case

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {self.key.token}"}, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "use_case_result",
        [
            ProviderAdapterValidationRequestError(provider_type=ProviderType.VLLM, errors=SAMPLE_VALIDATION_ERRORS),
            ProviderAdapterValidationResponseError(provider_type=ProviderType.VLLM, errors=SAMPLE_VALIDATION_ERRORS),
        ],
    )
    async def test_validation_error_returns_422_with_errors(self, client: AsyncClient, app, use_case_result):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_chat_completions_use_case_factory] = lambda: mock_use_case

        response = await client.post(url=URL, headers={"Authorization": f"Bearer {self.key.token}"}, json=_valid_body())

        assert response.status_code == 422
        assert response.json().get("detail") == SAMPLE_VALIDATION_ERRORS

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
