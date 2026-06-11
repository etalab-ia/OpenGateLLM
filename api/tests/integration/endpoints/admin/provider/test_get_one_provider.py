from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_one_provider_use_case_factory
from api.domain.provider.errors import ProviderNotFoundError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetProvider:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        provider = ProviderSQLFactory(router=router, user=self.admin_user, key="secret-key", basic_auth={"username": "u", "password": "p"})
        await db_session.flush()

        response = await client.get(
            url=f"{URL}/{provider.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == provider.id
        assert data["object"] == "provider"
        assert "key" not in data
        assert "basic_auth" not in data

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                ProviderNotFoundError(id=1),
                404,
                "Model provider 1 not found.",
            ),
            (
                UserIsNotAdminError(),
                403,
                "User has no admin rights.",
            ),
            (
                UserExpiredError(),
                403,
                "Your account has expired. Please contact support to renew your account.",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_one_provider_use_case_factory] = lambda: mock_use_case

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
