from collections.abc import AsyncGenerator
from unittest.mock import patch

from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy import select

from api.dependencies import get_postgres_session
from api.infrastructure.fastapi.endpoints.admin.providers import router as providers_router
from api.schemas.core.context import RequestContext
from api.schemas.models import ModelType
from api.schemas.usage import Usage
from api.sql.models import Provider as ProviderTable
from api.tests.helpers import create_token
from api.tests.integration.factories import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.context import request_context
from api.utils.dependencies import get_model_registry
from api.utils.dependencies import get_postgres_session as get_postgres_session_utils
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"


def _valid_body(router_id=1, **overrides) -> dict:
    """Return a minimal valid provider creation body, with optional overrides."""
    body = {
        "router": router_id,
        "type": "albert",
        "model_name": "my-model",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# Fake providers – the ONLY mock: external HTTP boundary
# ---------------------------------------------------------------------------


class FakeProvider:
    """Simulates an external model provider (health check calls)."""

    def __init__(self, url, key, timeout, model_name, model_hosting_zone, model_total_params, model_active_params):
        self.model_name = model_name

    async def get_max_context_length(self):
        return 4096

    async def get_vector_size(self):
        return 768


class UnreachableFakeProvider(FakeProvider):
    """provider whose health check fails."""

    async def get_max_context_length(self):
        raise AssertionError("provider not reachable")

    async def get_vector_size(self):
        raise AssertionError("provider not reachable")


class FakeProviderWithDifferentVectorSizeAndMaxContentLength(FakeProvider):
    """provider whose health check fails."""

    async def get_max_context_length(self):
        return 1234

    async def get_vector_size(self):
        return 1234


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def client(db_session, model_registry) -> AsyncGenerator[AsyncClient, None]:
    """Test client using a minimal app with only the new infrastructure providers router."""
    test_app = FastAPI()

    @test_app.middleware("http")
    async def set_request_context(request: Request, call_next):
        request_context.set(RequestContext(method=request.method, endpoint=request.url.path, usage=Usage()))
        return await call_next(request)

    test_app.include_router(providers_router)

    async def override_get_postgres_session():
        try:
            yield db_session
            if db_session.in_transaction():
                await db_session.flush()
        except Exception:
            if db_session.in_transaction():
                await db_session.rollback()
            raise

    test_app.dependency_overrides[get_postgres_session] = override_get_postgres_session
    test_app.dependency_overrides[get_postgres_session_utils] = override_get_postgres_session
    test_app.dependency_overrides[get_model_registry] = lambda: model_registry

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_import_module():
    """Patch ModelProvider.import_module so no real HTTP call is made."""
    with patch("api.helpers.models._modelregistry.ModelProvider.import_module") as mock:
        mock.return_value = FakeProvider
        yield mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio(loop_scope="session")
class TestCreateProvider:
    async def test_happy_path(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 201, response.text
        assert isinstance(response.json()["id"], int)

    async def test_no_auth_token(self, client: AsyncClient):
        response = await client.post(url=URL, json=_valid_body())

        assert response.status_code == 401

    async def test_missing_required_field(self, client: AsyncClient, db_session):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        body = {"type": "albert", "model_name": "my-model"}  # missing "router"

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=body,
        )

        assert response.status_code == 422

    async def test_invalid_provider_type(self, client: AsyncClient, db_session):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(type="not_a_real_provider"),
        )

        assert response.status_code == 422

    async def test_qos_metric_without_limit(self, client: AsyncClient, db_session):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(qos_metric="ttft"),
        )

        assert response.status_code == 422

    async def test_tei_type_requires_url(self, client: AsyncClient, db_session):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(type="tei"),
        )

        assert response.status_code == 422

    async def test_incompatible_provider_type(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id, type="tei", url="https://tei.example.com/"),
        )

        assert response.status_code == 400

    async def test_provider_not_reachable(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        mock_import_module.return_value = UnreachableFakeProvider

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 424

    async def test_provider_already_exists(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION)
        ProviderSQLFactory(
            router=router,
            user=admin_user,
            url="https://albert.api.etalab.gouv.fr/",
            model_name="my-model",
            max_context_length=4096,
            vector_size=None,
        )
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 409

    async def test_provider_mismatch_max_context_length(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_EMBEDDINGS_INFERENCE, name="test_router")
        ProviderSQLFactory(
            router=router,
            user=admin_user,
            url="https://albert.api.etalab.gouv.fr/",
            model_name="my-model",
            max_context_length=4096,
            vector_size=1234,
        )
        mock_import_module.return_value = FakeProviderWithDifferentVectorSizeAndMaxContentLength

        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "Inconsistent max context length for test_router. Expected: 1234. Actual: 4096"

    async def test_provider_mismatch_vector_size(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(
            db_session,
            name="admin_token",
            user=admin_user,
        )
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION, name="test_router")
        ProviderSQLFactory(
            router=router,
            user=admin_user,
            url="https://albert.api.etalab.gouv.fr/",
            model_name="my-model",
            max_context_length=4096,
            vector_size=1234,
        )
        mock_import_module.return_value = FakeProviderWithDifferentVectorSizeAndMaxContentLength

        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 403
        assert response.json().get("detail") == "Inconsistent vector size for test_router. Expected: None. Actual: 1234"

    async def test_router_not_found(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(999999),
        )

        assert response.status_code == 404

    async def test_url_trailing_slash(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id, url="https://my-provider.example.com"),
        )

        assert response.status_code == 201, response.text
        provider_id = response.json()["id"]
        result = await db_session.execute(select(ProviderTable.url).where(ProviderTable.id == provider_id))
        assert result.scalar_one() == "https://my-provider.example.com/"

    async def test_default_url_for_albert(self, client: AsyncClient, db_session, mock_import_module):
        admin_user = UserSQLFactory(admin_user=True)
        token = await create_token(db_session, name="admin_token", user=admin_user)
        router = RouterSQLFactory(user=admin_user, type=ModelType.TEXT_GENERATION)
        await db_session.flush()

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {token.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 201, response.text
        provider_id = response.json()["id"]
        result = await db_session.execute(select(ProviderTable.url).where(ProviderTable.id == provider_id))
        assert result.scalar_one() == "https://albert.api.etalab.gouv.fr/"
