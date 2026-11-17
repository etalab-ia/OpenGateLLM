from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.domain.provider.entities import ProviderType
from api.domain.router.entities import RouterType
from api.infrastructure.fastapi.routes import EndpointRoute
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_models_responses
from api.tests.integration.factories.sql import LimitSQLFactory, ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.tests.integration.factories.vllm import VllmModelsResponseFactory

HEALTH_URL = EndpointRoute.HEALTH
HEALTH_MODELS_URL = EndpointRoute.HEALTH_MODELS

HEALTH_MODEL_NAME = "health-model"


@pytest.mark.asyncio(loop_scope="session")
class TestGetHealth:
    async def test_should_return_ok(self, client: AsyncClient):
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

    @respx.mock
    async def test_should_return_the_status_of_the_models_the_user_can_access(self, client: AsyncClient, db_session):
        # Arrange
        router = RouterSQLFactory(
            user=self.router_owner,
            name="router_1",
            type=RouterType.TEXT_GENERATION,
        )
        ProviderSQLFactory(
            router=router,
            user=self.router_owner,
            type=ProviderType.VLLM,
            url=DEFAULT_PROVIDER_URL,
            model_name=HEALTH_MODEL_NAME,
        )
        RouterSQLFactory(
            user=self.router_owner,
            name="router_no_access",
            type=RouterType.TEXT_GENERATION,
            providers=1,
        )
        LimitSQLFactory(role=self.user.role, router=router)
        await db_session.flush()
        mock_models_responses(respx, ProviderType.VLLM, body=VllmModelsResponseFactory(), status_code=200)

        # Act
        response = await client.get(
            url=HEALTH_MODELS_URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
        )

        # Assert
        assert response.status_code == 200, response.text
        assert response.json() == {"data": [{"id": "router_1", "status": "green"}]}

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_should_return_401_when_the_key_is_missing_or_invalid(self, client: AsyncClient, headers, expected_status, expected_detail):
        # Act
        response = await client.get(url=HEALTH_MODELS_URL, headers=headers)

        # Assert
        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
