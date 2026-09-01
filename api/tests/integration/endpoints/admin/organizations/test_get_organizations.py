from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import OrganizationSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ORGANIZATIONS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetOrganizations:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        organization = OrganizationSQLFactory(name="my-organization")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["offset"] == 0
        assert data["limit"] == 10
        listed = {organization["name"]: organization for organization in data["data"]}
        assert listed["my-organization"]["id"] == organization.id

    async def test_applies_pagination_and_sort_query_params(self, client: AsyncClient, db_session):
        OrganizationSQLFactory(name="sort-a-organization")
        OrganizationSQLFactory(name="sort-b-organization")
        OrganizationSQLFactory(name="sort-c-organization")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            params={"offset": 0, "limit": 2, "sort_by": "id", "sort_order": "desc"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["offset"] == 0
        assert data["limit"] == 2
        assert len(data["data"]) == 2
        assert data["total"] > 2
        ids = [organization["id"] for organization in data["data"]]
        assert ids == sorted(ids, reverse=True)

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
