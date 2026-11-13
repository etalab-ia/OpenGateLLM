from collections.abc import AsyncGenerator

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from api.infrastructure.configuration import Configuration
from api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import UserSQLFactory

METRICS_URL = EndpointRoute.METRICS


@pytest_asyncio.fixture(scope="session")
async def metrics_client(create_test_app, test_configuration: Configuration) -> AsyncGenerator[AsyncClient, None]:
    settings = test_configuration.settings.model_copy(update={"monitoring_prometheus_enabled": True, "hidden_routers": [RouterName.MONITORING]})
    metrics_configuration = test_configuration.model_copy(update={"settings": settings})
    metrics_app = create_test_app(metrics_configuration)

    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio(loop_scope="session")
class TestGetMetrics:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_key = await create_key(db_session, name="admin_key", user=UserSQLFactory(admin_user=True), never_expires=True)
        self.regular_key = await create_key(db_session, name="regular_user_key", user=UserSQLFactory(regular_user=True), never_expires=True)

    async def test_should_return_the_metrics_when_the_key_belongs_to_an_admin(self, metrics_client: AsyncClient):
        # Act
        response = await metrics_client.get(url=METRICS_URL, headers={"Authorization": f"Bearer {self.admin_key.token}"})

        # Assert
        assert response.status_code == 200, response.text
        assert "ogl_inference_requests_total" in response.text

    @pytest.mark.parametrize(
        "headers,expected_detail",
        [
            ({}, "Not authenticated"),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, "Invalid API key."),
        ],
    )
    async def test_should_return_401_when_the_key_is_missing_or_invalid(self, metrics_client: AsyncClient, headers, expected_detail):
        # Act
        response = await metrics_client.get(url=METRICS_URL, headers=headers)

        # Assert
        assert response.status_code == 401, response.text
        assert response.json().get("detail") == expected_detail

    async def test_should_return_403_when_the_key_belongs_to_a_user_who_is_not_an_admin(self, metrics_client: AsyncClient):
        # Act
        response = await metrics_client.get(url=METRICS_URL, headers={"Authorization": f"Bearer {self.regular_key.token}"})

        # Assert
        assert response.status_code == 403, response.text
        assert response.json().get("detail") == "User has no admin rights."

    async def test_should_leave_metrics_out_of_the_openapi_schema_when_the_monitoring_router_is_hidden(self, metrics_client: AsyncClient):
        # Act
        response = await metrics_client.get(url="/openapi.json")

        # Assert
        assert METRICS_URL not in response.json()["paths"]
