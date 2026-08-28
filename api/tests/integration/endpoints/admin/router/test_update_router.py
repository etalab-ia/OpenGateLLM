from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import update_router_use_case_factory
from api.domain.model.entities import ModelType
from api.domain.router.entities import RouterLoadBalancingStrategy
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


def _valid_body(**overrides) -> dict:
    body = {
        "name": "updated-name",
        "type": ModelType.TEXT_GENERATION,
        "aliases": [],
        "load_balancing_strategy": RouterLoadBalancingStrategy.SHUFFLE,
        "cost_prompt_tokens": 0.0,
        "cost_completion_tokens": 0.0,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateRouter:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_overrides(self, app):
        yield
        app.dependency_overrides.pop(update_router_use_case_factory, None)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, name="original-name")
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(aliases=["alias-1"], cost_prompt_tokens=0.5, cost_completion_tokens=1.5),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == router.id
        assert data["name"] == "updated-name"
        assert data["aliases"] == ["alias-1"]
        assert data["type"] == ModelType.TEXT_GENERATION
        assert data["load_balancing_strategy"] == RouterLoadBalancingStrategy.SHUFFLE
        assert data["cost_prompt_tokens"] == 0.5
        assert data["cost_completion_tokens"] == 1.5
        assert data["object"] == "router"

    async def test_clears_aliases_sent_as_an_empty_list(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, alias=["alias-1"])
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(aliases=[]),
        )

        assert response.status_code == 200, response.text
        assert response.json()["aliases"] == []

    async def test_rejects_body_missing_a_required_field(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={"name": "updated-name"},
        )

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(id=1),
                404,
                "Model router 1 not found.",
            ),
            (
                RouterNameAlreadyExistsError(name="taken-name"),
                409,
                "Router taken-name already exists.",
            ),
            (
                RouterAliasAlreadyExistsError(aliases=["alias1"]),
                409,
                "Following aliases already exist: '['alias1']'",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_router_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.patch(
            url=f"{URL}/1",
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
        response = await client.patch(url=f"{URL}/1", headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
