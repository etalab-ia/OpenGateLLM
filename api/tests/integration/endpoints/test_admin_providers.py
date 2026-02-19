import httpx
from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.schemas.models import ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"

DEFAULT_PROVIDER_URL = "http://my-test-provider/"


def _valid_body(router_id=1, **overrides) -> dict:
    """Return a minimal valid provider creation body, with optional overrides."""
    body = {
        "router": router_id,
        "type": "albert",
        "model_name": "my-model",
        "url": DEFAULT_PROVIDER_URL,
    }
    body.update(overrides)
    return body


def _mock_provider_reachable(respx_mock, base_url=DEFAULT_PROVIDER_URL, max_context_length=4096, vector_size=768):
    """Mock GET /v1/models and POST /v1/embeddings for a reachable albert provider."""
    base_url = base_url.rstrip("/")
    respx_mock.get(f"{base_url}/v1/models").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"id": "my-model", "aliases": [], "max_context_length": max_context_length}],
            },
        )
    )
    embedding = [0.0] * vector_size if vector_size else []
    respx_mock.post(f"{base_url}/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"embedding": embedding}],
            },
        )
    )


def _mock_provider_unreachable(respx_mock, base_url=DEFAULT_PROVIDER_URL):
    """Mock a provider that cannot be reached."""
    base_url = base_url.rstrip("/")
    respx_mock.get(f"{base_url}/v1/models").mock(side_effect=httpx.ConnectError("connection refused"))
    respx_mock.post(f"{base_url}/v1/embeddings").mock(side_effect=httpx.ConnectError("connection refused"))


@pytest.mark.asyncio(loop_scope="session")
class TestCreateProvider:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()
        _mock_provider_reachable(respx)
        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 201, response.text
        assert isinstance(response.json()["id"], int)

    @respx.mock
    async def test_incompatible_provider_type(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()
        _mock_provider_reachable(respx, base_url="https://tei.example.com")

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router.id, type="tei", url="https://tei.example.com/"),
        )

        assert response.status_code == 400
        assert response.json().get("detail") == "Invalid model provider type tei for text-generation router."

    @respx.mock
    async def test_provider_not_reachable(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()
        _mock_provider_unreachable(respx)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 424
        assert response.json().get("detail") == "Model provider my-model not reachable."

    @respx.mock
    async def test_provider_already_exists(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_GENERATION)
        ProviderSQLFactory(
            router=router,
            user=self.admin_user,
            url=DEFAULT_PROVIDER_URL,
            model_name="my-model",
            max_context_length=4096,
            vector_size=None,
        )
        await db_session.flush()
        _mock_provider_reachable(respx)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router.id),
        )
        assert response.status_code == 409
        assert response.json().get("detail") == "Model provider my-model for url http://my-test-provider/ already exists for router 4."

    @respx.mock
    async def test_provider_mismatch_max_context_length(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_EMBEDDINGS_INFERENCE, name="test_router")
        ProviderSQLFactory(
            router=router,
            user=self.admin_user,
            url="https://albert.api.etalab.gouv.fr/",
            model_name="my-model",
            max_context_length=4096,
            vector_size=1234,
        )
        await db_session.flush()
        _mock_provider_reachable(respx, max_context_length=1234, vector_size=1234)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "Inconsistent max context length for test_router. Expected: 1234. Actual: 4096"

    @respx.mock
    async def test_provider_mismatch_vector_size(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=ModelType.TEXT_GENERATION, name="test_router")
        ProviderSQLFactory(
            router=router,
            user=self.admin_user,
            url="https://albert.api.etalab.gouv.fr/",
            model_name="my-model",
            max_context_length=4096,
            vector_size=1234,
        )
        await db_session.flush()
        _mock_provider_reachable(respx, max_context_length=1234, vector_size=1234)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "Inconsistent vector size for test_router. Expected: None. Actual: 1234"

    @respx.mock
    async def test_router_not_found(self, client: AsyncClient, db_session):
        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(999999),
        )

        assert response.status_code == 404
        assert response.json().get("detail") == "Model router 999999 not found."
