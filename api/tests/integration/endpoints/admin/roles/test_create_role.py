from unittest.mock import AsyncMock, create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_role_authorization, create_role_use_case_factory
from api.domain.role import RoleAuthorization
from api.domain.role.errors import RoleAlreadyExistsError, UserCannotCreateRoleError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UserSQLFactory

URL = f"/v1{EndpointRoute.ADMIN_ROLES}"


def _valid_body(**overrides) -> dict:
    body = {"name": "new-role"}
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateRole:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @pytest.fixture
    def mock_role_authorization(self, app):
        # No OpenFGA server in the tests: the port answers in its place.
        mock_authorization = create_autospec(RoleAuthorization, instance=True, spec_set=True)
        mock_authorization.can_create_role.return_value = True
        app.dependency_overrides[_get_role_authorization] = lambda: mock_authorization
        return mock_authorization

    async def test_should_return_the_role_when_the_user_is_allowed_to_create_it(self, client: AsyncClient, db_session, mock_role_authorization):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 201, response.text
        mock_role_authorization.can_create_role.assert_awaited_once_with(user_id=self.admin_user.id)
        data = response.json()
        assert data["name"] == "new-role"
        assert isinstance(data["id"], int)
        assert data["permissions"] == []
        assert data["limits"] == []

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RoleAlreadyExistsError(name="existing-role"),
                409,
                "Role existing-role already exists.",
            ),
            (
                UserCannotCreateRoleError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_role_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
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
    async def test_should_reject_the_request_when_the_key_is_missing_or_invalid(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
