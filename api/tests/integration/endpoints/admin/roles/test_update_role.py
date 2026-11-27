from unittest.mock import AsyncMock, create_autospec

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import _get_role_authorization, update_role_use_case_factory
from api.domain.role import RoleAuthorization
from api.domain.role.entities import LimitType, PermissionType
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError, UserCannotUpdateRoleError
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory

URL = f"/v1{EndpointRoute.ADMIN_ROLES}"


def _valid_body(**overrides) -> dict:
    """A full update payload: every persisted field is required."""
    body = {"name": "updated-role", "permissions": [], "limits": []}
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateRole:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @pytest.fixture
    def mock_role_authorization(self, app):
        # No OpenFGA server in the tests: the port answers in its place.
        mock_authorization = create_autospec(RoleAuthorization, instance=True, spec_set=True)
        mock_authorization.can_update_role.return_value = True
        app.dependency_overrides[_get_role_authorization] = lambda: mock_authorization
        return mock_authorization

    async def test_should_return_the_updated_role_when_the_user_is_allowed_to_update_it(
        self, client: AsyncClient, db_session, mock_role_authorization
    ):
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{role.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(
                name="updated-role",
                permissions=[PermissionType.PROVIDE_MODELS],
                limits=[{"router_id": router.id, "type": LimitType.RPM, "value": 10}],
            ),
        )

        assert response.status_code == 200, response.text
        mock_role_authorization.can_update_role.assert_awaited_once_with(user_id=self.admin_user.id, role_id=role.id)
        data = response.json()
        assert data["id"] == role.id
        assert data["object"] == "role"
        assert data["name"] == "updated-role"
        assert data["permissions"] == [PermissionType.PROVIDE_MODELS]
        assert data["limits"] == [{"router_id": router.id, "type": LimitType.RPM, "value": 10}]

    async def test_should_clear_permissions_and_limits_when_they_are_sent_as_empty_lists(
        self, client: AsyncClient, db_session, mock_role_authorization
    ):
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{role.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(permissions=[], limits=[]),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["permissions"] == []
        assert data["limits"] == []

    async def test_should_return_422_when_the_body_misses_a_required_field(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{role.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={"name": "updated-role"},
        )

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RoleNotFoundError(id=1),
                404,
                "Role 1 not found.",
            ),
            (
                RoleAlreadyExistsError(name="existing-role"),
                409,
                "Role existing-role already exists.",
            ),
            (
                UserCannotUpdateRoleError(user_id=7),
                403,
                "User 7 is not allowed to perform this action.",
            ),
        ],
    )
    async def test_should_map_each_domain_error_to_its_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_role_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=f"{URL}/1",
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
        response = await client.patch(url=f"{URL}/1", headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
