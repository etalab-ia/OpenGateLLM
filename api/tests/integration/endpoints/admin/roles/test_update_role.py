from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import update_role_use_case_factory
from api.domain.role.entities import LimitType, PermissionType
from api.domain.role.errors import RoleAlreadyExistsError, RoleNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import LimitSQLFactory, PermissionSQLFactory, RoleSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

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

    async def test_happy_path(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        response = await client.put(
            url=f"{URL}/{role.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(
                name="updated-role",
                permissions=[PermissionType.ADMIN],
                limits=[{"router_id": router.id, "type": LimitType.RPM, "value": 10}],
            ),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == role.id
        assert data["object"] == "role"
        assert data["name"] == "updated-role"
        assert data["permissions"] == [PermissionType.ADMIN]
        assert data["limits"] == [{"router_id": router.id, "type": LimitType.RPM, "value": 10}]

    async def test_clears_permissions_and_limits_sent_as_empty_lists(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        router = RouterSQLFactory()
        LimitSQLFactory(role=role, router=router, type=LimitType.TPM, value=100)
        PermissionSQLFactory(role=role, permission=PermissionType.READ_METRIC)
        await db_session.flush()

        response = await client.put(
            url=f"{URL}/{role.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(permissions=[], limits=[]),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["permissions"] == []
        assert data["limits"] == []

    async def test_rejects_body_missing_a_required_field(self, client: AsyncClient, db_session):
        role = RoleSQLFactory()
        await db_session.flush()

        response = await client.put(
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
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_role_use_case_factory] = lambda: mock_use_case

        response = await client.put(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.put(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {key.token}"},
            json=_valid_body(),
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
        response = await client.put(url=f"{URL}/1", headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
