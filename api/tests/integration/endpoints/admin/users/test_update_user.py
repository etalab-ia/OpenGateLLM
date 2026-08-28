import datetime as dt
from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import update_user_use_case_factory
from api.domain.organization.errors import OrganizationNotFoundError
from api.domain.role.errors import RoleNotFoundError
from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import OrganizationSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_USERS}"


def _valid_body(**overrides) -> dict:
    body = {
        "email": "updated@example.com",
        "name": "Updated Name",
        "role_id": 1,
        "organization_id": None,
        "budget": None,
        "expires": None,
        "priority": 0,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateUser:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        user = UserSQLFactory()
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{user.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(role_id=user.role_id, budget=50.5, priority=2),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == user.id
        assert data["email"] == "updated@example.com"
        assert data["name"] == "Updated Name"
        assert data["budget"] == 50.5
        assert data["priority"] == 2
        assert data["role_id"] == user.role_id

    async def test_clears_nullable_fields_sent_as_null(self, client: AsyncClient, db_session):
        organization = OrganizationSQLFactory()
        user = UserSQLFactory(organization=organization, budget=100.0, expires=dt.datetime.now() + dt.timedelta(days=30))
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{user.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(role_id=user.role_id, name=None, organization_id=None, budget=None, expires=None),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["name"] is None
        assert data["organization_id"] is None
        assert data["budget"] is None
        assert data["expires"] is None

    async def test_accepts_past_expiration_timestamp(self, client: AsyncClient, db_session):
        user = UserSQLFactory()
        await db_session.flush()
        expires = int((dt.datetime.now(tz=dt.UTC) - dt.timedelta(minutes=5)).timestamp())

        response = await client.patch(
            url=f"{URL}/{user.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(role_id=user.role_id, expires=expires),
        )

        assert response.status_code == 200, response.text
        assert response.json()["expires"] == expires

    async def test_keeps_password_when_password_is_omitted(self, client: AsyncClient, db_session):
        user = UserSQLFactory()
        current_password = user.password
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{user.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(role_id=user.role_id),
        )

        assert response.status_code == 200, response.text
        await db_session.refresh(user)
        assert user.password == current_password

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({key: value for key, value in _valid_body().items() if key != "email"}, id="missing-required-field"),
            pytest.param(_valid_body(email=None), id="null-on-non-nullable-field"),
        ],
    )
    async def test_rejects_incomplete_body(self, client: AsyncClient, db_session, body):
        user = UserSQLFactory()
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{user.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=body,
        )

        assert response.status_code == 422, response.text

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserNotFoundError(id=1),
                404,
                "User 1 not found.",
            ),
            (
                UserAlreadyExistsError(email="taken@example.com"),
                409,
                "User taken@example.com already exists.",
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
                IncorrectCurrentPasswordError(user_id=1),
                401,
                "Invalid current password.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_user_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.patch(
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
        response = await client.patch(url=f"{URL}/1", headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
