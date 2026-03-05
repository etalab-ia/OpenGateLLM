from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_providers_use_case_factory
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetProviders:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    async def test_happy_path_without_params(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        for i in range(1, 8):
            ProviderSQLFactory(router=router, model_name=f"model_{i}")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["total"] == 7
        assert data["offset"] == 0
        assert data["limit"] == 10
        assert len(data["data"]) == 7

    async def test_happy_path_with_params(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        for i in range(1, 8):
            ProviderSQLFactory(router=router, model_name=f"model_{i}")
        await db_session.flush()

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            params={"offset": 3, "limit": 3},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["total"] == 7
        assert data["offset"] == 3
        assert data["limit"] == 3
        assert len(data["data"]) == 3

    async def test_pagination_limit_should_be_less_than_100(self, client: AsyncClient):
        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            params={"offset": 0, "limit": 101},
        )

        assert response.status_code == 422, response.text
        assert response.json().get("detail")[0]["msg"] == "Input should be less than or equal to 100"

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
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
        app.dependency_overrides[get_providers_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
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
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
