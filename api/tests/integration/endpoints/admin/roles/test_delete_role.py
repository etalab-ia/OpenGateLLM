from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import delete_role_use_case_factory
from api.domain.role.errors import RoleHasUsersError, RoleNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories.sql import RoleSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROLES}"


@pytest.mark.asyncio(loop_scope="session")
class TestDeleteRole:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        role = RoleSQLFactory(name="to-delete")
        await db_session.flush()

        response = await client.delete(
            url=f"{URL}/{role.id}",
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == role.id
        assert data["name"] == "to-delete"

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RoleNotFoundError(role_id=999),
                404,
                "Role 999 not found.",
            ),
            (
                RoleHasUsersError(role_id=999, number_of_users=3),
                409,
                "Role 999 has 3 users and cannot be removed.",
            ),
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
        app.dependency_overrides[delete_role_use_case_factory] = lambda: mock_use_case

        response = await client.delete(
            url=f"{URL}/999",
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
        response = await client.delete(url=f"{URL}/1", headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
