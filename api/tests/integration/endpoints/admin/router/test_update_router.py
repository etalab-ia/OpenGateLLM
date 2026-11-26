from unittest.mock import AsyncMock, create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_router_authorization, update_router_use_case_factory
from api.domain.router import RouterAuthorization
from api.domain.router.entities import RouterType
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, RouterNotFoundError, UserCannotUpdateRouterError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


def _valid_body(**overrides) -> dict:
    body = {
        "name": "updated-name",
        "type": RouterType.TEXT_GENERATION,
        "aliases": [],
        "qos_retries_before_reject": 2,
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

    @pytest.fixture
    def mock_router_authorization(self, app):
        # No OpenFGA server in the tests: the port answers in its place.
        mock_authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
        mock_authorization.can_update_router.return_value = True
        app.dependency_overrides[_get_router_authorization] = lambda: mock_authorization
        return mock_authorization

    async def test_should_return_the_updated_router_when_the_user_is_allowed_to_update_it(
        self, client: AsyncClient, db_session, mock_router_authorization
    ):
        router = RouterSQLFactory(user=self.admin_user, name="original-name")
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(aliases=["alias-1"], cost_prompt_tokens=0.5, cost_completion_tokens=1.5),
        )

        assert response.status_code == 200, response.text
        mock_router_authorization.can_update_router.assert_awaited_once_with(user_id=self.admin_user.id, router_id=router.id)
        data = response.json()
        assert data["id"] == router.id
        assert data["name"] == "updated-name"
        assert data["aliases"] == ["alias-1"]
        assert data["type"] == RouterType.TEXT_GENERATION
        assert data["qos_retries_before_reject"] == 2
        assert data["cost_prompt_tokens"] == 0.5
        assert data["cost_completion_tokens"] == 1.5
        assert data["object"] == "router"

    async def test_should_clear_aliases_sent_as_an_empty_list(self, client: AsyncClient, db_session, mock_router_authorization):
        router = RouterSQLFactory(user=self.admin_user, alias=["alias-1"])
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(aliases=[]),
        )

        assert response.status_code == 200, response.text
        assert response.json()["aliases"] == []

    async def test_should_reject_a_body_missing_a_required_field(self, client: AsyncClient, db_session):
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
            (
                UserCannotUpdateRouterError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
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

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_should_reject_the_request_when_the_key_is_missing_or_invalid(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.patch(url=f"{URL}/1", headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
