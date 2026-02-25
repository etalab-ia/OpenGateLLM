from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_one_router_use_case_factory
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.schemas.models import ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetRouter:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_overrides(self, app):
        yield
        app.dependency_overrides.pop(get_one_router_use_case_factory, None)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        response = await client.get(
            url=f"{URL}/{router.id}",
            headers={"Authorization": f"Bearer {self.token.token}"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == router.id
        assert data["object"] == "router"

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(router_id=1),
                404,
                "Model router 1 not found.",
            ),
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
        app.dependency_overrides[get_one_router_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=f"{URL}/1",
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
        response = await client.get(url=f"{URL}/1", headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
