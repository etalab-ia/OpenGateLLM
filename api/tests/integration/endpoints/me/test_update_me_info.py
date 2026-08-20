from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import update_me_info_use_case_factory
from api.domain.user.errors import IncorrectCurrentPasswordError, UserAlreadyExistsError, UserNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ME_INFO}"


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateMeInfo:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True, name="Original Name", email="original@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user, never_expires=True)

    async def test_happy_path(self, client: AsyncClient, db_session):
        response = await client.patch(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={"email": "updated@example.com", "name": "Updated Name"},
        )

        assert response.status_code == 204, response.text
        assert response.content == b""

        await db_session.refresh(self.user)
        assert self.user.email == "updated@example.com"
        assert self.user.name == "Updated Name"

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
                IncorrectCurrentPasswordError(user_id=1),
                401,
                "Invalid current password.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_me_info_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={},
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
        response = await client.patch(url=URL, headers=headers, json={})

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
