from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import create_router_use_case_factory
from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.infrastructure.modeltokenizer import CachedModelTokenizerLoader
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UserSQLFactory
from api.tests.integration.globalcontext import override_global_context

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


def _valid_body(**overrides) -> dict:
    body = {
        "name": "test-router",
        "type": "text-generation",
        "aliases": [],
        "qos_retries_before_reject": 4,
        "cost_prompt_tokens": 0.001,
        "cost_completion_tokens": 0.002,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateRouter:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @pytest.fixture(autouse=True)
    def _real_model_tokenizer_loader(self):
        with override_global_context(model_tokenizer_loader=CachedModelTokenizerLoader(default_tokenizer="tiktoken_gpt2")):
            yield

    async def test_happy_path(self, client: AsyncClient, db_session):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(name="test-router-1", aliases=["alias_1", "alias_2"]),
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert isinstance(data.get("id"), int)
        assert data.get("aliases") == ["alias_1", "alias_2"]
        assert data["qos_retries_before_reject"] == 4

    async def test_should_return_the_tokenizer_when_it_can_be_loaded(self, client: AsyncClient, db_session):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(name="test-router-tokenizer", tokenizer="tiktoken_o200k_base"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["tokenizer"] == "tiktoken_o200k_base"

    async def test_should_return_a_null_tokenizer_when_none_is_given(self, client: AsyncClient, db_session):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(name="test-router-no-tokenizer"),
        )

        assert response.status_code == 201, response.text
        assert response.json()["tokenizer"] is None

    async def test_should_return_422_when_the_tokenizer_cannot_be_loaded(self, client: AsyncClient, db_session, monkeypatch):
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(name="test-router-bad-tokenizer", tokenizer="unknown-org/unknown-model"),
        )

        assert response.status_code == 422, response.text
        assert "unknown-org/unknown-model" in response.json()["detail"]

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNameAlreadyExistsError(name="test-router"),
                409,
                "Router test-router already exists.",
            ),
            (
                RouterAliasAlreadyExistsError(aliases=["alias1"]),
                409,
                "Following aliases already exist: '['alias1']'",
            ),
            (
                ModelTokenizerNotLoadableError(tokenizer="unknown/model", detail="not found"),
                422,
                "Tokenizer unknown/model cannot be loaded: not found",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_router_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 403, response.text
        assert response.json().get("detail") == "User has no admin rights."

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
