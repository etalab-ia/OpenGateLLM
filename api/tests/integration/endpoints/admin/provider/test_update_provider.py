from unittest.mock import AsyncMock

from httpx import AsyncClient
import pytest
import pytest_asyncio

from api.dependencies import update_provider_use_case_factory
from api.domain.model.errors import InconsistentModelMaxContextLengthError, InconsistentModelVectorSizeError
from api.domain.provider.entities import HostingZone, QoSMetric
from api.domain.provider.errors import InvalidProviderTypeError, ProviderAlreadyExistsError, ProviderNotFoundError
from api.domain.router.errors import RouterNotFoundError
from api.tests.helpers import INVALID_API_KEY, create_key
from api.tests.integration.factories.sql import ProviderSQLFactory, RouterSQLFactory, UserSQLFactory
from api.utils.variables import EndpointRoute

URL = f"/v1{EndpointRoute.ADMIN_PROVIDERS}"

DEFAULT_PROVIDER_URL = "http://my-test-provider/"


def _valid_body(**overrides) -> dict:
    """A full update payload: every persisted field is required."""
    body = {
        "router_id": 1,
        "timeout": 120,
        "model_hosting_zone": HostingZone.FRA,
        "model_total_params": 8,
        "model_active_params": 2,
        "qos_metric": None,
        "qos_limit": None,
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio(loop_scope="session")
class TestUpdateProvider:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session):
        self.admin_user = UserSQLFactory(admin_user=True)
        self.key = await create_key(db_session, name="admin_key", user=self.admin_user)

    async def test_happy_path(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        provider = ProviderSQLFactory(router=router, user=self.admin_user, timeout=30)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{provider.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(router_id=router.id, qos_metric=QoSMetric.TTFT, qos_limit=0.9),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == provider.id
        assert data["object"] == "provider"
        assert data["router_id"] == router.id
        assert data["timeout"] == 120
        assert data["model_hosting_zone"] == HostingZone.FRA
        assert data["model_total_params"] == 8
        assert data["model_active_params"] == 2
        assert data["qos_metric"] == QoSMetric.TTFT
        assert data["qos_limit"] == 0.9

    async def test_clears_qos_policy_sent_as_null(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        provider = ProviderSQLFactory(router=router, user=self.admin_user, qos_metric=QoSMetric.TTFT, qos_limit=0.9)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{provider.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(router_id=router.id, qos_metric=None, qos_limit=None),
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["qos_metric"] is None
        assert data["qos_limit"] is None

    async def test_rejects_body_missing_a_required_field(self, client: AsyncClient, db_session):
        router = RouterSQLFactory(user=self.admin_user)
        provider = ProviderSQLFactory(router=router, user=self.admin_user)
        await db_session.flush()

        response = await client.patch(
            url=f"{URL}/{provider.id}",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json={"timeout": 120},
        )

        assert response.status_code == 422, response.text

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
                400,
                "Inconsistent max context length for my-router. Expected: 4096. Actual: 2048",
            ),
            (
                InconsistentModelVectorSizeError(expected_vector_size=768, actual_vector_size=384, router_name="my-router"),
                400,
                "Inconsistent vector size for my-router. Expected: 768. Actual: 384",
            ),
        ],
    )
    async def test_error_maps_to_correct_http_status(self, client: AsyncClient, app, use_case_result, expected_status, expected_detail):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[update_provider_use_case_factory] = lambda: mock_use_case

        response = await client.patch(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {self.key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail

    async def test_rejects_non_admin_user(self, client: AsyncClient, db_session):
        regular_user = UserSQLFactory(regular_user=True)
        key = await create_key(db_session, name="regular_user_key", user=regular_user, never_expires=True)

        response = await client.patch(
            url=f"{URL}/1",
            headers={"Authorization": f"Bearer {key.token}"},
            json=_valid_body(),
        )

        assert response.status_code == 403, response.text
        assert response.json().get("detail") == "User has no admin rights."

    @pytest.mark.parametrize(
        "headers,expected_status,expected_detail",
        [
            ({}, 401, "Not authenticated"),
            ({"Authorization": "Bearer malformed-token"}, 401, "Invalid API key."),
            ({"Authorization": f"Bearer {INVALID_API_KEY}"}, 401, "Invalid API key."),
        ],
    )
    async def test_auth(self, client: AsyncClient, headers, expected_status, expected_detail):
        response = await client.patch(url=f"{URL}/1", headers=headers, json=_valid_body())

        assert response.status_code == expected_status
        assert response.json().get("detail") == expected_detail
