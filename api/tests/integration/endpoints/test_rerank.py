from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_rerank_use_case_factory
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.schemas.admin.roles import LimitType
from api.schemas.models import ModelType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_rerank_responses
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.tests.integration.factories.tei import TeiRerankResponseFactory
from api.utils.context import global_context
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.RERANK}"

DEFAULT_MODEL_NAME = "rerank-router"
DEFAULT_QUERY = "The sun is shining."
DEFAULT_DOCUMENTS = [
    "The document is about the weather.",
    "The document is about the news.",
    "The document is about the sports.",
]
SAMPLE_VALIDATION_ERRORS = [{"type": "missing", "loc": ["query"], "msg": "Field required", "input": {}}]


def _valid_body(**overrides) -> dict:
    body = {
        "model": DEFAULT_MODEL_NAME,
        "query": DEFAULT_QUERY,
        "documents": DEFAULT_DOCUMENTS,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateRerank:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)
        previous_redis_pool = global_context.redis_pool
        previous_tokenizer = getattr(global_context, "_tokenizer", None)
        global_context.redis_pool = test_redis_pool

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [0] * 10
        global_context._tokenizer = mock_tokenizer

        yield

        global_context.redis_pool = previous_redis_pool
        global_context._tokenizer = previous_tokenizer

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_rerank_key", user=self.router_owner)
        router = RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.TEXT_CLASSIFICATION,
            providers=1,
            providers__type=ProviderType.TEI,
            providers__url=DEFAULT_PROVIDER_URL,
        )
        await db_session.flush()

        mock_rerank_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiRerankResponseFactory(count=len(DEFAULT_DOCUMENTS)),
            status_code=TeiRerankResponseFactory._status_code,
        )

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["model"] == DEFAULT_MODEL_NAME
        assert len(data["results"]) == len(DEFAULT_DOCUMENTS)
        assert all("relevance_score" in result and "index" in result for result in data["results"])

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(name=DEFAULT_MODEL_NAME),
                404,
                f"Model {DEFAULT_MODEL_NAME} not found.",
            ),
            (
                RouterHasNoProvidersError(id=1),
                404,
                f"Model {DEFAULT_MODEL_NAME} not found.",
            ),
            (
                UserHasNoAccessToRouterError(id=1),
                404,
                f"Model {DEFAULT_MODEL_NAME} not found.",
            ),
            (
                UserHasInsufficientBudgetError(),
                400,
                "Insufficient budget.",
            ),
            (
                RouterHasWrongTypeError(id=1, actual_type=RouterType.TEXT_GENERATION, expected_type=RouterType.TEXT_CLASSIFICATION),
                422,
                "Model has wrong type. Expected: text-classification. Actual: text-generation.",
            ),
            (
                NoAvailableProviderError(router_id=1),
                503,
                "Model is too busy, please try again later.",
            ),
            (
                TooBusyModelError(status_code=503, detail="provider busy"),
                503,
                "Model is too busy, please try again later.",
            ),
            (
                RouterRateLimitExceededError(id=1, limit_type=LimitType.RPM, headers={}),
                429,
                "Request limit per minute exceeded.",
            ),
            (
                StatusCodeModelError(status_code=400, detail="bad request"),
                400,
                "bad request",
            ),
            (
                UnknownModelError(status_code=500, detail="upstream failure"),
                500,
                "upstream failure",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_rerank_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "use_case_result",
        [
            ProviderAdapterValidationRequestError(provider_type=ProviderType.TEI, errors=SAMPLE_VALIDATION_ERRORS),
            ProviderAdapterValidationResponseError(provider_type=ProviderType.TEI, errors=SAMPLE_VALIDATION_ERRORS),
        ],
    )
    async def test_adapter_validation_error_returns_422_with_errors(self, client: AsyncClient, app, use_case_result):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_rerank_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

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
