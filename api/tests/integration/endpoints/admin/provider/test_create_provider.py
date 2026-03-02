from unittest.mock import AsyncMock

import httpx
from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_provider_use_case_factory
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.schemas.models import ModelType
from api.tests.helpers import create_token
from api.tests.integration.factories import RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"

DEFAULT_PROVIDER_URL = "http://my-test-provider/"


def _valid_body(router_id: int, **overrides) -> dict:
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


@pytest.mark.asyncio(loop_scope="session")
class TestCreateProvider:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup_overrides(self, app):
        yield
        app.dependency_overrides.pop(create_provider_use_case_factory, None)

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

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(router_id=1),
                404,
                "Model router 1 not found.",
            ),
            (
                InvalidProviderTypeError(provider_type="tei", router_type="text-generation"),
                400,
                "Invalid model provider type tei for text-generation router.",
            ),
            (
                ProviderNotReachableError(model_name="my-model"),
                424,
                "Model provider my-model not reachable.",
            ),
            (
                ProviderAlreadyExistsError(model_name="my-model", url=DEFAULT_PROVIDER_URL, router_id=1),
                409,
                f"Model provider my-model for url {DEFAULT_PROVIDER_URL} already exists for router 1.",
            ),
            (
                InconsistentModelMaxContextLengthError(expected_max_context_length=4096, actual_max_context_length=2048, router_name="my-router"),
                403,
                "Inconsistent max context length for my-router. Expected: 4096. Actual: 2048",
            ),
            (
                InconsistentModelVectorSizeError(expected_vector_size=768, actual_vector_size=384, router_name="my-router"),
                403,
                "Inconsistent vector size for my-router. Expected: 768. Actual: 384",
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
        app.dependency_overrides[create_provider_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.token.token}"},
            json=_valid_body(router_id=1),
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
        response = await client.post(url=URL, headers=headers, json=_valid_body(router_id=1))

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
