from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio
import respx

from api.dependencies import create_provider_use_case_factory
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotReachableError
from api.domain.router.errors import RouterNotFoundError
from api.domain.user.errors import UserExpiredError, UserIsNotAdminError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.endpoints.utils import DEFAULT_PROVIDER_URL, mock_models_responses
from api.tests.integration.factories.albert import AlbertModelResponseFactory, AlbertModelsResponseFactory
from api.tests.integration.factories.sql import RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"


DEFAULT_MODEL_ID = "test/my-model"
DEFAULT_MAX_CONTEXT_LENGTH = 4096


def _valid_body(router_id: int, **overrides) -> dict:
    """Return a minimal valid provider creation body, with optional overrides."""
    body = {
        "router_id": router_id,
        "type": ProviderType.ALBERT.value,
        "model_name": DEFAULT_MODEL_ID,
        "url": DEFAULT_PROVIDER_URL,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestCreateProvider:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    @respx.mock
    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user, type=RouterType.TEXT_GENERATION)
        await db_session.flush()
        mock_models_responses(
            respx_mock=respx,
            provider_type=ProviderType.ALBERT,
            body=AlbertModelsResponseFactory(
                data=[AlbertModelResponseFactory(model=DEFAULT_MODEL_ID, max_context_length=DEFAULT_MAX_CONTEXT_LENGTH)],
                count=3,
            ),
            status_code=AlbertModelsResponseFactory._status_code,
        )

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(router.id),
        )

        assert response.status_code == 201, response.text
        assert isinstance(response.json()["id"], int)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                RouterNotFoundError(id=1),
                404,
                "Model router 1 not found.",
            ),
            (
                InvalidProviderTypeError(provider_type="tei", router_type="text-generation"),
                400,
                "Invalid model provider type tei for text-generation router.",
            ),
            (
                ProviderNotReachableError(model_name="my-model", status_code=500, detail="error_detail"),
                424,
                "Model provider my-model not reachable (500): error_detail",
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
        app.dependency_overrides[create_provider_use_case_factory] = lambda: mock_use_case

        response = await client.post(
            url=URL,
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(router_id=1),
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
        response = await client.post(url=URL, headers=headers, json=_valid_body(router_id=1))

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
