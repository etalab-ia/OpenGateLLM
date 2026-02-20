from collections.abc import AsyncGenerator
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient
import pytest

from api.app import create_app
from api.utils.variables import EndpointRoute, RouterName


@pytest.fixture(scope="class")
def test_configuration():
    return SimpleNamespace(
        settings=SimpleNamespace(
            app_title="test",
            swagger_summary=None,
            swagger_version="0.0.0",
            swagger_description=None,
            swagger_terms_of_service=None,
            swagger_contact=None,
            swagger_license_info=None,
            swagger_openapi_tags=[],
            swagger_docs_url="/test-swagger",
            swagger_redoc_url="/test-redoc",
            session_secret_key="test-secret-key",
            disabled_routers=[RouterName.ADMIN],
            hidden_routers=[RouterName.MODELS],
            monitoring_prometheus_enabled=False,
        ),
        dependencies=SimpleNamespace(sentry=None),
    )


@pytest.fixture(scope="class")
async def client(test_configuration) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(test_configuration, skip_lifespan=True)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio(loop_scope="session")
class TestCreateApp:
    async def test_reach_swagger_with_non_default_url_configuration_is_reachable(self, client: AsyncClient, test_configuration: SimpleNamespace):
        # Act
        response = await client.get(url=test_configuration.settings.swagger_docs_url)

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    async def test_redoc_with_non_default_url_configuration_is_reachable(self, client: AsyncClient, test_configuration: SimpleNamespace):
        # Act
        response = await client.get(url=test_configuration.settings.swagger_redoc_url)

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    async def test_exposed_openapi_schema_is_reachable(self, client: AsyncClient):
        # Act
        response = await client.get(url="/openapi.json")

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    async def test_enabled_router_is_reachable(self, client: AsyncClient, test_configuration: SimpleNamespace):
        # Act
        response = await client.get(url=f"/v1{EndpointRoute.ME_INFO}")

        # Assert
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    async def test_disabled_router_is_unreachable(self, client: AsyncClient, test_configuration: SimpleNamespace):
        # Act
        response = await client.get(url=f"/v1/{test_configuration.settings.disabled_routers[0]}")

        # Assert
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    async def test_hidden_router_is_reachable(self, client: AsyncClient, test_configuration: SimpleNamespace):
        # Act
        response = await client.get(url=f"/v1/{test_configuration.settings.hidden_routers[0]}")

        # Assert
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    async def test_hidden_router_is_not_in_exposed_openapi_schema(self, client: AsyncClient, test_configuration: SimpleNamespace):
        # Act
        response = await client.get(url="/openapi.json")

        # Assert
        hidden_router_path = f"/v1/{test_configuration.settings.hidden_routers[0]}"
        assert hidden_router_path not in response.json()["paths"], f"Hidden route {hidden_router_path} is exposed in OpenAPI schema"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
