import logging
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import CreateProvider, ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import CreateRouter
from api.schemas.models import ModelType
from api.tests.integ.utils import kill_openmockllm, run_openmockllm
from api.utils.variables import ENDPOINT__ADMIN_PROVIDERS, ENDPOINT__ADMIN_ROUTERS

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def text_generation_vllm_model(name: str = None) -> tuple[str, str]:
    model_name = f"text-generation-model-{uuid4()}"
    port = 8090
    process = run_openmockllm(port=port, model_name=model_name, backend="vllm")

    yield model_name, f"http://localhost:{port}"

    kill_openmockllm(process=process, port=port, model_name=model_name)


@pytest.fixture(scope="module")
def text_embeddings_inference_tei_model() -> tuple[str, str]:
    model_name = f"text-embeddings-inference-model-{uuid4()}"
    port = 8091
    process = run_openmockllm(port=port, model_name=model_name, backend="tei")

    yield model_name, f"http://localhost:{port}"

    kill_openmockllm(process=process, port=port, model_name=model_name)


@pytest.fixture(scope="module")
def text_generation_router(client: TestClient) -> int:
    """Get an existing text-generation router from config"""
    payload = CreateRouter(name=f"test-router-{uuid4()}", type=ModelType.TEXT_GENERATION)
    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROUTERS}", json=payload.model_dump())
    assert response.status_code == 201, response.text

    router_id = response.json()["id"]

    yield router_id

    client.delete_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROUTERS}/{router_id}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="module")
def text_embeddings_inference_router(client: TestClient) -> int:
    """Get an existing text-embeddings-inference router from config"""
    payload = CreateRouter(name=f"test-router-{uuid4()}", type=ModelType.TEXT_EMBEDDINGS_INFERENCE)
    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROUTERS}", json=payload.model_dump())
    assert response.status_code == 201, response.text
    router_id = response.json()["id"]

    yield router_id

    client.delete_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROUTERS}/{router_id}")
    assert response.status_code == 204, response.text


@pytest.mark.usefixtures("client")
class TestAdminProviders:
    def test_create_provider_with_text_generation_model(
        self,
        client: TestClient,
        text_generation_vllm_model: tuple[str, str],
        text_generation_router: int,
    ):
        model_name, url = text_generation_vllm_model
        router_id = text_generation_router

        payload = CreateProvider(
            router=router_id,
            type=ProviderType.VLLM,
            url=url,
            key=None,  # Mock server doesn't require authentication
            timeout=10,
            model_name=model_name,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=None,
            model_carbon_footprint_active_params=None,
            qos_metric=None,
            qos_threshold=None,
        )

        response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_PROVIDERS}", json=payload.model_dump())
        assert response.status_code == 201, response.text

    def test_create_router_with_text_embeddings_inference_model(
        self,
        client: TestClient,
        text_embeddings_inference_tei_model: tuple[str, str],
        text_embeddings_inference_router: int,
    ):
        model_name, url = text_embeddings_inference_tei_model
        router_id = text_embeddings_inference_router

        payload = CreateProvider(
            router=router_id,
            type=ProviderType.TEI,
            url=url,
            key=None,  # Mock server doesn't require authentication
            timeout=10,
            model_name=model_name,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=None,
            model_carbon_footprint_active_params=None,
            qos_metric=None,
            qos_threshold=None,
        )

        response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_PROVIDERS}", json=payload.model_dump())
        assert response.status_code == 201, response.text
