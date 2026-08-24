from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import create_me_key_use_case_factory
from api.domain.key.errors import KeyAlreadyExistsError, KeyExpirationInvalidError
from api.domain.user.errors import UserNotFoundError
from api.tests.helpers import create_key
from api.tests.integration.factories.sql import UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.KEYS}"


def _valid_body(**overrides) -> dict:
    body = {"name": "new-key"}
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateMeKey:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(regular_user=True)
        self.token = await create_key(db_session, name="user_token", user=self.user)

    async def test_happy_path(self, client: AsyncClient):
        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert data["object"] == "key"
        assert data["name"] == "new-key"
        assert data["user"] == self.user.id
        assert isinstance(data["id"], int)
        assert data["value"].startswith("sk-")
        assert data["expires"] is None
        assert isinstance(data["created"], int)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                KeyAlreadyExistsError(name="new-key"),
                409,
                "Key new-key already exists.",
            ),
            (
                KeyExpirationInvalidError(max_expiration_days=365),
                400,
                "Key expiration timestamp cannot be greater than 365 days from now.",
            ),
            (
                UserNotFoundError(id=99),
                404,
                "User 99 not found.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_me_key_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer invalid-token"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
