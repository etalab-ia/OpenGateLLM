from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import create_router_use_case_factory
from api.domain.router.errors import RouterAliasAlreadyExistsError, RouterNameAlreadyExistsError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories import UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_ROUTERS}"


def _valid_body(**overrides) -> dict:
    body = {
        "name": "test-router",
        "type": "text-generation",
        "aliases": [],
        "load_balancing_strategy": "shuffle",
        "cost_prompt_tokens": 0.001,
        "cost_completion_tokens": 0.002,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateRouter:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_overrides(self, app):
        yield
        app.dependency_overrides.pop(create_router_use_case_factory, None)

    async def test_happy_path(self, client: AsyncClient, db_session):
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(name="test-router-1", aliases=["alias_1", "alias_2"]),
        )

        assert response.status_code == 201, response.text
        data = response.json()
        assert isinstance(data.get("id"), int)
        assert data.get("aliases") == ["alias_1", "alias_2"]

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                UserIsNotAdminError(),
                403,
                "User has no admin rights.",
            ),
            (
                RouterNameAlreadyExistsError(name="test-router"),
                409,
                "Router test-router already exists.",
            ),
            (
                RouterAliasAlreadyExistsError(aliases=["alias1"]),
                409,
                "Following aliases already exist: '['alias1']'",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_router_use_case_factory] = lambda: mock_use_case

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
            ({"Authorization": "Bearer invalid-token"}, 403, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.post(url=URL, headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
