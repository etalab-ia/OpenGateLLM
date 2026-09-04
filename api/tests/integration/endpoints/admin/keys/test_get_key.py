from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_one_key_use_case_factory
from api.domain.key.errors import KeyNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import KeySQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_KEYS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetKey:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        user = UserSQLFactory()
        key = KeySQLFactory(user=user, name="my-key", never_expires=True)
        await db_session.flush()

        response = await client.get(
            url=f"{URL}/{key.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == key.id
        assert data["object"] == "key"
        assert data["name"] == "my-key"
        assert data["user_id"] == user.id

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                KeyNotFoundError(id=1),
                404,
                "Key 1 not found.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_one_key_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.get(
            url=f"{URL}/1",
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
        response = await client.get(url=f"{URL}/1", headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
