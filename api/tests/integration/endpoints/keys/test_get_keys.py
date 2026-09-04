from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import KeySQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.KEYS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetMeKeys:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True)
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    async def test_happy_path(self, client: AsyncClient, db_session):
        own_key = KeySQLFactory(user=self.user, name="own-key", never_expires=True)
        other_user = UserSQLFactory()
        KeySQLFactory(user=other_user, name="other-key", never_expires=True)
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["total"] == 2
        assert data["offset"] == 0
        assert data["limit"] == 10
        assert len(data["data"]) == 2
        assert all(item["object"] == "key" for item in data["data"])
        assert all(item["user"] == self.user.id for item in data["data"])
        returned_ids = {item["id"] for item in data["data"]}
        assert own_key.id in returned_ids
        assert self.key.id in returned_ids

    async def test_excludes_expired_keys_by_default(self, client: AsyncClient, db_session):
        expired_key = KeySQLFactory(user=self.user, name="expired-key", expired=True)
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert expired_key.id not in {item["id"] for item in data["data"]}

    async def test_includes_expired_keys_when_requested(self, client: AsyncClient, db_session):
        expired_key = KeySQLFactory(user=self.user, name="expired-key", expired=True)
        await db_session.flush()

        response = await client.get(
            url=URL,
            params={"include_expired": True},
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        returned = {item["id"] for item in data["data"]}
        assert expired_key.id in returned
        assert self.key.id in returned

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
