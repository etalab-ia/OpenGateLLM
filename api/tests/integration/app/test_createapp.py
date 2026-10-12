from collections.abc import AsyncGenerator

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from api.app import create_app
from api.infrastructure.configuration import Configuration, Dependencies, Settings
from api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from api.tests.helpers import create_key


@pytest.fixture(scope="session")
def createapp_configuration() -> Configuration:
    return Configuration.model_construct(
        settings=Settings.model_construct(
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
            disabled_routers=[RouterName.ADMIN],
            hidden_routers=[RouterName.MODELS],
            monitoring_prometheus_enabled=False,
        ),
        dependencies=Dependencies.model_construct(sentry=None),
    )


@pytest_asyncio.fixture(scope="session")
async def createapp_client(createapp_configuration) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(createapp_configuration, skip_lifespan=True)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio(loop_scope="session")
class TestCreateApp:
    async def test_reach_swagger_with_non_default_url_configuration_is_reachable(
        self, createapp_client: AsyncClient, createapp_configuration: Configuration
    ):
        # Act
        response = await createapp_client.get(url=createapp_configuration.settings.swagger_docs_url)

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    async def test_redoc_with_non_default_url_configuration_is_reachable(self, createapp_client: AsyncClient, createapp_configuration: Configuration):
        # Act
        response = await createapp_client.get(url=createapp_configuration.settings.swagger_redoc_url)

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    async def test_exposed_openapi_schema_is_reachable(self, createapp_client: AsyncClient):
        # Act
        response = await createapp_client.get(url="/openapi.json")

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    async def test_enabled_router_is_reachable(self, createapp_client: AsyncClient, createapp_configuration: Configuration):
        # Act
        response = await createapp_client.get(url=f"/v1{EndpointRoute.ME}")

        # Assert
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    async def test_disabled_router_is_unreachable(self, createapp_client: AsyncClient, createapp_configuration: Configuration):
        # Act
        response = await createapp_client.get(url=f"/v1/{createapp_configuration.settings.disabled_routers[0]}")

        # Assert
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    async def test_hidden_router_is_reachable(self, createapp_client: AsyncClient, createapp_configuration: Configuration):
        # Act
        response = await createapp_client.get(url=f"/v1/{createapp_configuration.settings.hidden_routers[0]}")

        # Assert
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    async def test_hidden_router_is_not_in_exposed_openapi_schema(self, createapp_client: AsyncClient, createapp_configuration: Configuration):
        # Act
        response = await createapp_client.get(url="/openapi.json")

        # Assert
        hidden_router_path = f"/v1/{createapp_configuration.settings.hidden_routers[0]}"
        assert hidden_router_path not in response.json()["paths"], f"Hidden route {hidden_router_path} is exposed in OpenAPI schema"


@pytest.mark.asyncio(loop_scope="session")
class TestCreateAppRequestDependencies:
    async def test_accepts_a_key_signed_with_the_secret_of_the_configuration_given_to_create_app(
        self, client: AsyncClient, db_session, test_configuration: Configuration
    ):
        # Arrange
        key = await create_key(db_session, secret_key=test_configuration.settings.auth_secret_key, never_expires=True)

        # Act
        response = await client.get(url=f"/v1{EndpointRoute.ME}", headers={"Authorization": f"Bearer {key.token}"})

        # Assert
        assert response.status_code == 200, response.text

    async def test_rejects_a_key_signed_with_another_secret(self, client: AsyncClient, db_session):
        # Arrange
        key = await create_key(db_session, secret_key="another-secret", never_expires=True)

        # Act
        response = await client.get(url=f"/v1{EndpointRoute.ME}", headers={"Authorization": f"Bearer {key.token}"})

        # Assert
        assert response.status_code == 401, response.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
