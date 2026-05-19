from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import get_health_models_use_case_factory
from api.domain.provider.entities import Metric
from api.domain.user.errors import UserExpiredError
from api.schemas.models import ModelType
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.redis import RedisMetricsFactory
from api.tests.integration.factories.sql import LimitSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

HEALTH_URL = EndpointRoute.HEALTH
HEALTH_MODELS_URL = EndpointRoute.HEALTH_MODELS

LATENCY_HISTORY_COUNT = 1800
MEDIAN_LATENCY_MS = 1000.0
HISTORICAL_LATENCIES_MS = [MEDIAN_LATENCY_MS] * LATENCY_HISTORY_COUNT


@pytest.mark.asyncio(loop_scope="session")
class TestGetHealth:
    async def test_happy_path(self, client: AsyncClient):
        response = await client.get(url=HEALTH_URL)

        assert response.status_code == 200, response.text
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
class TestGetHealthModels:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.user = UserSQLFactory(name="Alice", email="alice@example.com")
        self.key = await create_key(db_session, name="user_key", user=self.user)
        self.router_owner = UserSQLFactory(name="Bob", email="bob@example.com", admin_user=True)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(
            user=self.router_owner,
            name="router_1",
            type=ModelType.TEXT_GENERATION,
            providers=1,
            providers__qos_metric=None,
        )
        RouterSQLFactory(
            user=self.router_owner,
            name="router_no_access",
            type=ModelType.TEXT_GENERATION,
            providers=1,
            providers__qos_metric=None,
        )
        LimitSQLFactory(role=self.user.role, router=router)
        await db_session.flush()

        response = await client.get(
            url=HEALTH_MODELS_URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        assert response.status_code == 200, response.text
        assert response.json() == {"data": [{"id": "router_1", "status": "green"}]}

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
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
        app.dependency_overrides[get_health_models_use_case_factory] = lambda: mock_use_case

        response = await client.get(
            url=HEALTH_MODELS_URL,
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
        response = await client.get(url=HEALTH_MODELS_URL, headers=headers)

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
