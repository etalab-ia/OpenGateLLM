from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_one_key_use_case_factory
from api.domain.key.errors import KeyNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import KeySQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.KEYS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetMeKey:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True)
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    async def test_happy_path(self, client: AsyncClient):
        response = await client.get(
            url=f"{URL}/{self.key.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "key"
        assert data["id"] == self.key.id
        assert data["name"] == "user_key"
        assert data["user_id"] == self.user.id
        assert data["value"] == self.key.token
        assert data["expires"] is None
        assert isinstance(data["created"], int)

    async def test_returns_not_found_for_another_users_key(self, client: AsyncClient, db_session):
        other_user = UserSQLFactory()
        other_key = KeySQLFactory(user=other_user, name="other-key", never_expires=True)
        await db_session.flush()

        response = await client.get(
            url=f"{URL}/{other_key.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 404, response.text
        assert response.json().get("detail") == f"Key {other_key.id} not found."

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
