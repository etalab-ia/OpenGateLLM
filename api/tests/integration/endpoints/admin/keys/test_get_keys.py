from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import KeySQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_KEYS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetKeys:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        user = UserSQLFactory()
        KeySQLFactory(user=user, name="key-a", never_expires=True)
        KeySQLFactory(user=user, name="key-b", never_expires=True)
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["total"], int)
        assert data["offset"] == 0
        assert data["limit"] == 10
        assert len(data["data"]) >= 2
        assert all(item["object"] == "key" for item in data["data"])

    async def test_filters_by_user(self, client: AsyncClient, db_session):
        user = UserSQLFactory()
        other_user = UserSQLFactory()
        key = KeySQLFactory(user=user, name="user-key", never_expires=True)
        KeySQLFactory(user=other_user, name="other-key", never_expires=True)
        await db_session.flush()

        response = await client.get(
            url=URL,
            params={"user": user.id},
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["id"] == key.id
        assert data["data"][0]["user_id"] == user.id

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
