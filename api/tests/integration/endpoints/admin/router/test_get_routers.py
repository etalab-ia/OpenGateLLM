from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_routers_use_case_factory
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories import RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouters:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_overrides(self, app):
        yield
        app.dependency_overrides.pop(get_routers_use_case_factory, None)

    async def test_happy_path_without_params(self, client: AsyncClient, db_session):
        RouterSQLFactory(user=self.admin_user, name="router_1")
        RouterSQLFactory(user=self.admin_user, name="router_2")
        RouterSQLFactory(user=self.admin_user, name="router_3")
        RouterSQLFactory(user=self.admin_user, name="router_4")
        RouterSQLFactory(user=self.admin_user, name="router_5")
        RouterSQLFactory(user=self.admin_user, name="router_6")
        RouterSQLFactory(user=self.admin_user, name="router_7")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["total"] == 7
        assert data["offset"] == 0
        assert data["limit"] == 10
        assert len(data["data"]) == 7

    async def test_happy_path_with_params(self, client: AsyncClient, db_session):
        RouterSQLFactory(user=self.admin_user, name="router_1")
        RouterSQLFactory(user=self.admin_user, name="router_2")
        RouterSQLFactory(user=self.admin_user, name="router_3")
        RouterSQLFactory(user=self.admin_user, name="router_4")
        RouterSQLFactory(user=self.admin_user, name="router_5")
        RouterSQLFactory(user=self.admin_user, name="router_6")
        RouterSQLFactory(user=self.admin_user, name="router_7")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            params={"offset": 3, "limit": 3},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        returned_names = [r["name"] for r in data["data"]]
        assert data["object"] == "list"
        assert data["total"] == 7
        assert data["offset"] == 3
        assert data["limit"] == 3
        assert len(data["data"]) == 3
        assert returned_names == ["router_4", "router_5", "router_6"]

    async def test_pagination_limit_should_be_less_than_100(self, client: AsyncClient, db_session):
        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            params={"offset": 0, "limit": 101},
        )
        assert response.status_code == 422, response.text
        assert response.json().get("detail")[0]["msg"] == "Input should be less than or equal to 100"

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserIsNotAdminError(),
                403,
                "User has no admin rights.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_routers_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer invalid-token"}, 403, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
