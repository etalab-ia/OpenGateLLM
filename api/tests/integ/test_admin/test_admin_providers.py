import logging

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import CreateProvider, ProviderCarbonFootprintZone, ProviderType
from api.schemas.models import ModelType
from api.tests.integ.utils import create_router, generate_test_id, kill_openmockllm, run_openmockllm
from api.utils.variables import ENDPOINT__ADMIN_PROVIDERS

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def setup_text_generation_router(client: TestClient):
    test_id = generate_test_id(prefix="TestAdminProviders")
    process = run_openmockllm(test_id=test_id, backend="vllm")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.TEXT_GENERATION, client=client)

        yield router_id, process.model_name, process.url

    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


@pytest.fixture(scope="module")
def setup_text_embeddings_inference_router(client: TestClient):
    test_id = generate_test_id(prefix="TestAdminProviders")
    process = run_openmockllm(test_id=test_id, backend="tei")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.TEXT_EMBEDDINGS_INFERENCE, client=client)

        yield router_id, process.model_name, process.url
    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


@pytest.mark.usefixtures("client")
class TestAdminProviders:
    def test_create_provider_with_text_generation_model(self, client: TestClient, setup_text_generation_router: tuple[int, str]):
        router_id, model_name, url = setup_text_generation_router

        payload = CreateProvider(
            router=router_id,
            type=ProviderType.VLLM,
            url=url,
            key=None,  # Mock server doesn't require authentication
            timeout=10,
            model_name=model_name,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
        )

        response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_PROVIDERS}", json=payload.model_dump())
        assert response.status_code == 201, response.text

    def test_create_router_with_text_embeddings_inference_model(self, client: TestClient, setup_text_embeddings_inference_router: tuple[int, str]):
        router_id, model_name, url = setup_text_embeddings_inference_router

        payload = CreateProvider(
            router=router_id,
            type=ProviderType.TEI,
            url=url,
            key=None,  # Mock server doesn't require authentication
            timeout=10,
            model_name=model_name,
            model_carbon_footprint_zone=ProviderCarbonFootprintZone.WOR,
            model_carbon_footprint_total_params=0,
            model_carbon_footprint_active_params=0,
            qos_metric=None,
            qos_limit=None,
        )

        response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_PROVIDERS}", json=payload.model_dump())
        assert response.status_code == 201, response.text
