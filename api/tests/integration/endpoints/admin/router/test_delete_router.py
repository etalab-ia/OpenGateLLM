from unittest.mock import AsyncMock, create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_router_authorization, delete_router_use_case_factory
from api.domain.router import RouterAuthorization
from api.domain.router.errors import RouterNotFoundError, UserCannotDeleteRouterError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteRouter:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @pytest.fixture
    def mock_router_authorization(self, app):
        # No OpenFGA server in the tests: the port answers in its place.
        mock_authorization = create_autospec(RouterAuthorization, instance=True, spec_set=True)
        mock_authorization.can_delete_router.return_value = True
        app.dependency_overrides[_get_router_authorization] = lambda: mock_authorization
        return mock_authorization

    async def test_should_return_the_router_when_the_user_is_allowed_to_delete_it(self, client: AsyncClient, db_session, mock_router_authorization):
        router = RouterSQLFactory(user=self.admin_user)
        await db_session.flush()

        response = await client.delete(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        mock_router_authorization.can_delete_router.assert_awaited_once_with(user_id=self.admin_user.id, router_id=router.id)
        data = response.json()
        assert data["id"] == router.id
        assert data["object"] == "router"

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(id=1),
                404,
                "Model router 1 not found.",
            ),
            (
                UserCannotDeleteRouterError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[delete_router_use_case_factory] = lambda: mock_use_case

        response = await client.delete(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.key.token}"},
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
        response = await client.delete(url=f"{URL}/1", headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
