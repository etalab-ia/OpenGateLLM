from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import OrganizationSQLFactory, RoleSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_USERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetUsers:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        role = RoleSQLFactory(name="my-role")
        UserSQLFactory(role=role)
        UserSQLFactory(role=role)
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["total"], int)
        assert isinstance(data["offset"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 2

    async def test_filters_by_role_id(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        user_1 = UserSQLFactory(role=role)
        user_2 = UserSQLFactory(role=role)
        UserSQLFactory()
        await db_session.flush()

        response = await client.get(
            url=URL,
            params={"role_id": role.id},
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] == 2
        result_ids = {u["id"] for u in data["data"]}
        assert result_ids == {user_1.id, user_2.id}

    async def test_filters_by_email_partial_match(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        user = UserSQLFactory(role=role, email="target@test.com")
        UserSQLFactory(role=role, email="other@test.com")
        await db_session.flush()

        response = await client.get(
            url=URL,
            params={"email": "target"},
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] == 1
        assert [u["id"] for u in data["data"]] == [user.id]

    async def test_filters_by_organization_id(self, client: AsyncClient, db_session):
        organization = OrganizationSQLFactory()
        user_1 = UserSQLFactory(organization=organization)
        user_2 = UserSQLFactory(organization=organization)
        UserSQLFactory()
        await db_session.flush()

        response = await client.get(
            url=URL,
            params={"organization_id": organization.id},
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["total"] == 2
        result_ids = {u["id"] for u in data["data"]}
        assert result_ids == {user_1.id, user_2.id}

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
