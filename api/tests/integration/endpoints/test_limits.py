from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.domain.role.entities import LimitType
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import LimitSQLFactory, RouterSQLFactory, UserSQLFactory
from api.tests.integration.globalcontext import override_global_context

URL = f"/v1{EndpointRoute.LIMITS}"


@pytest.mark.asyncio(loop_scope="session")
class TestGetLimits:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session, test_redis_pool):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)
        with override_global_context(redis_pool=test_redis_pool):
            yield

    async def test_happy_path(self, client: AsyncClient, db_session):
        # Arrange
        router = RouterSQLFactory(user=self.router_owner, name="router_1", providers=1)
        limits = {LimitType.TPM: None, LimitType.TPD: 10000, LimitType.RPM: 20, LimitType.RPD: 10000}
        for limit_type, value in limits.items():
            LimitSQLFactory(role=self.user.role, router=router, type=limit_type, value=value)
        await db_session.flush()

        # Act
        response = await client.get(url=URL, headers={"Authorization": f"Bearer {self.key.token}"})

        # Assert
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["object"] == "list"
        assert data["data"] == [
            {"object": "limit", "router_id": router.id, "model": "router_1", "type": "tpm", "value": None, "remaining": 0},
            {"object": "limit", "router_id": router.id, "model": "router_1", "type": "tpd", "value": 10000, "remaining": 10000},
            {"object": "limit", "router_id": router.id, "model": "router_1", "type": "rpm", "value": 20, "remaining": 20},
            {"object": "limit", "router_id": router.id, "model": "router_1", "type": "rpd", "value": 10000, "remaining": 10000},
        ]

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.get(url=URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
