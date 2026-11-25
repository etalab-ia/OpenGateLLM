from unittest.mock import AsyncMock, create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_router_authorization, create_router_use_case_factory
from api.domain.router import RouterAuthorization
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError, UserCannotCreateRouterError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UserSQLFactory

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

    @pytest.fixture
    def mock_router_authorization(self, app):
        # No OpenFGA server in the tests: the port answers in its place.
        mock_authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
        mock_authorization.can_create_router.return_value = True
        app.dependency_overrides[_get_router_authorization] = lambda: mock_authorization
        return mock_authorization

    async def test_should_return_the_router_when_the_user_is_allowed_to_create_it(self, client: AsyncClient, db_session, mock_router_authorization):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(name="test-router-1", aliases=["alias_1", "alias_2"]),
        )

        assert response.status_code == 201, response.text
        mock_router_authorization.can_create_router.assert_awaited_once_with(user_id=self.admin_user.id)
        data = response.json()
        assert isinstance(data.get("id"), int)
        assert data.get("aliases") == ["alias_1", "alias_2"]
        assert data["qos_retries_before_reject"] == 4

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
                UserCannotCreateRouterError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
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

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_should_reject_the_request_when_the_key_is_missing_or_invalid(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
