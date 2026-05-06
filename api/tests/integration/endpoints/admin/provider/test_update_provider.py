from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import update_provider_use_case_factory
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotFoundError
from api.domain.router.errors import RouterNotFoundError
from api.domain.userinfo.errors import UserIsNotAdminError
from api.tests.helpers import create_token
from api.tests.integration.factories.sql import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"

DEFAULT_PROVIDER_URL = "http://my-test-provider/"


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateProvider:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.token = await create_token(db_session, name="admin_token", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        provider = ProviderSQLFactory(router=router, user=self.admin_user, timeout=30)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{provider.id}",
            headers={"Authorization": f"Bearer {self.token.token}"},
            json={"timeout": 120},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == provider.id
        assert data["object"] == "provider"
        assert data["timeout"] == 120

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (
                ProviderNotFoundError(id=1),
                404,
                "Model provider 1 not found.",
            ),
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
        app.dependency_overrides[update_provider_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.token.token}"},
            json={"timeout": 120},
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
        response = await client.patch(url=f"{URL}/1", headers=headers, json={"timeout": 120})

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
