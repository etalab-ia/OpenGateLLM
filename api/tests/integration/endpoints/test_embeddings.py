import json
from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_embeddings_use_case_factory
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.role.entities import LimitType
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.schemas.models import ModelType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.conftest import override_global_context
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_embeddings_responses
from api.tests.integration.factories.sql import LimitSQLFactory, RouterSQLFactory, UserSQLFactory
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.EMBEDDINGS}"

DEFAULT_MODEL_NAME = "embeddings-router"
DEFAULT_INPUT = "The sun is shining."
MOCKED_PROMPT_TOKENS = 10
SAMPLE_VALIDATION_ERRORS = [{"type": "missing", "loc": ["input"], "msg": "Field required", "input": {}}]


def _valid_body(**overrides) -> dict:
    body = {
        "model": DEFAULT_MODEL_NAME,
        "input": DEFAULT_INPUT,
    }
    body.update(overrides)
    return body


def _allow_requests(role, router) -> None:
    # set both high to leave TPM the only gate
    LimitSQLFactory(role=role, router=router, type=LimitType.RPM, value=1000)
    LimitSQLFactory(role=role, router=router, type=LimitType.RPD, value=1000)


@pytest.mark.asyncio(loop_scope="session")
class TestCreateEmbeddings:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [0] * MOCKED_PROMPT_TOKENS
        with override_global_context(redis_pool=test_redis_pool, _tokenizer=mock_tokenizer):
            yield

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_embeddings_key", user=self.router_owner)
        router = RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            providers=1,
            providers__type=ProviderType.TEI,
            providers__url=DEFAULT_PROVIDER_URL,
        )
        await db_session.flush()

        mock_embeddings_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiEmbeddingsResponseFactory(),
            status_code=TeiEmbeddingsResponseFactory._status_code,
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
        assert len(data["data"]) >= 1
        assert all("embedding" in item and "index" in item for item in data["data"])

    @respx.mock
    async def test_omitted_optional_fields_are_excluded_from_provider_body(self, client: AsyncClient, db_session):
        admin_key = await create_key(db_session, name="admin_embeddings_exclude_none_key", user=self.router_owner)
        RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            providers=1,
            providers__type=ProviderType.TEI,
            providers__url=DEFAULT_PROVIDER_URL,
        )
        await db_session.flush()

        route = mock_embeddings_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiEmbeddingsResponseFactory(),
            status_code=TeiEmbeddingsResponseFactory._status_code,
        )

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {admin_key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 200, response.text
        provider_json = json.loads(route.calls[0].request.content)
        assert "dimensions" not in provider_json
        assert None not in provider_json.values()

    @respx.mock
    async def test_prompt_larger_than_remaining_tokens_returns_429(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            providers=1,
            providers__type=ProviderType.TEI,
            providers__url=DEFAULT_PROVIDER_URL,
        )
        _allow_requests(role=self.user.role, router=router)
        # one token short of what the mocked tokenizer charges for the prompt, so the fresh window cannot fit it
        LimitSQLFactory(role=self.user.role, router=router, type=LimitType.TPM, value=MOCKED_PROMPT_TOKENS - 1)
        await db_session.flush()

        # the provider answers 200 here, so a 429 can only come from a rejection made before the forward
        route = mock_embeddings_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiEmbeddingsResponseFactory(),
            status_code=TeiEmbeddingsResponseFactory._status_code,
        )

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 429, response.text
        assert response.json().get("detail") == "Token limit per minute exceeded."
        assert not route.called

    @respx.mock
    async def test_prompt_larger_than_window_left_by_a_previous_request_returns_429(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(
            user=self.router_owner,
            name=DEFAULT_MODEL_NAME,
            type=ModelType.TEXT_EMBEDDINGS_INFERENCE,
            providers=1,
            providers__type=ProviderType.TEI,
            providers__url=DEFAULT_PROVIDER_URL,
        )
        _allow_requests(role=self.user.role, router=router)
        # room for one prompt but not for two, so only the window left by the first request can reject the second
        LimitSQLFactory(role=self.user.role, router=router, type=LimitType.TPM, value=2 * MOCKED_PROMPT_TOKENS - 1)
        await db_session.flush()

        route = mock_embeddings_responses(
            respx_mock=respx,
            provider_type=ProviderType.TEI,
            body=TeiEmbeddingsResponseFactory(),
            status_code=TeiEmbeddingsResponseFactory._status_code,
        )
        headers = {"Authorization": f"Bearer {self.key.token}"}

        first_response = await client.post(url=URL, headers=headers, json=_valid_body())
        second_response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert first_response.status_code == 200, first_response.text
        assert second_response.status_code == 429, second_response.text
        assert second_response.json().get("detail") == "Token limit per minute exceeded."
        assert route.call_count == 1

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
                RouterHasWrongTypeError(id=1, actual_type=RouterType.TEXT_GENERATION, expected_type=RouterType.TEXT_EMBEDDINGS_INFERENCE),
                422,
                "Model has wrong type. Expected: text-embeddings-inference. Actual: text-generation.",
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
        app.dependency_overrides[create_embeddings_use_case_factory] = lambda: mock_use_case

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
        app.dependency_overrides[create_embeddings_use_case_factory] = lambda: mock_use_case

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
