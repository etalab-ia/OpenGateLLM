from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import create_user_use_case_factory
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import UserAlreadyExistsError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories.sql import RoleSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_USERS}"


def _valid_body(role_id: int, **overrides) -> dict:
    body = {
        "email": "newuser@test.com",
        "password": "s3cr3t",
        "role": role_id,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateUser:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(role_id=role.id),
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert isinstance(data["id"], int)
        assert data["role"] == role.id

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserAlreadyExistsError(email="existing@test.com"),
                409,
                "User existing@test.com already exists.",
            ),
            (
                RoleNotFoundError(id=99),
                404,
                "Role 99 not found.",
            ),
            (
                OrganizationNotFoundError(id=99),
                404,
                "Organization 99 not found.",
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
        app.dependency_overrides[create_user_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(role_id=1),
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
        response = await client.post(url=URL, headers=headers, json=_valid_body(role_id=1))

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
