from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_users_use_case_factory
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
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

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserIsNotAdminError(),
                403,
                "User has no admin rights.",
            ),
            (
                UserExpiredError(),
                403,
                "Your account has expired. Please contact support to renew your account.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_users_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=URL,
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
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
