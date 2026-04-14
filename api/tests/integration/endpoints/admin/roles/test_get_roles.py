from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_roles_use_case_factory
from api.domain.role.entities import LimitType, PermissionType
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROLES}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetRoles:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory()
        role = RoleSQLFactory(name="my-role")
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["total"], int)
        assert isinstance(data["offset"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        role_names = [r["name"] for r in data["data"]]
        assert "my-role" in role_names

    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = UserIsNotAdminError()
        app.dependency_overrides[get_roles_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "User has no admin rights."

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
