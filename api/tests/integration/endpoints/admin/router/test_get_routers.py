from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouters:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

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
            headers={"Authorization": f"Bearer {self.key.token}"},
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
        expected_routers_ordered_by_name = ["router_4", "router_5", "router_6"]
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
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
        assert returned_names == expected_routers_ordered_by_name

    async def test_pagination_limit_should_be_less_than_100(self, client: AsyncClient, db_session):
        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            params={"offset": 0, "limit": 101},
        )
        assert response.status_code == 422, response.text
        assert response.json().get("detail")[0]["msg"] == "Input should be less than or equal to 100"

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {key.token}"},
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
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
