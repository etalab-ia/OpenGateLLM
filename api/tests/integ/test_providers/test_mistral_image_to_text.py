import datetime as dt

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import ProviderType
from api.schemas.models import ModelType
from api.schemas.ocr import OCR
from api.tests.integ.utils import (
    create_provider,
    create_role,
    create_router,
    create_token,
    create_user,
    generate_test_id,
    kill_openmockllm,
    run_openmockllm,
)
from api.utils.variables import EndpointRoute


@pytest.fixture(scope="module")
def setup_mistral_image_to_text(client: TestClient):
    test_id = generate_test_id(prefix="TestUsage")
    process = run_openmockllm(test_id=test_id, backend="mistral")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.IMAGE_TO_TEXT, client=client)
        create_provider(
            router_id=router_id,
            provider_url=process.url,
            provider_key=None,
            provider_name=process.model_name,
            provider_type=ProviderType.MISTRAL,
            client=client,
        )
        role_id = create_role(router_id=router_id, client=client)
        user_id = create_user(role_id=role_id, client=client)
        _, key = create_token(user_id=user_id, token_name=f"test-token-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}", client=client)

        yield key, process.model_name
    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


@pytest.mark.usefixtures("client", "setup_mistral_image_to_text")
class TestMistralImageToText:
    def test_mistral_ocr_successful(self, client: TestClient, setup_mistral_image_to_text: tuple[str, str]):
        """Test successful OCR processing of a PDF file."""

        key, model_name = setup_mistral_image_to_text

        response = client.post(
            f"/v1{EndpointRoute.OCR}",
            json={"model": model_name, "document": {"type": "document_url", "document_url": "https://www.princexml.com/samples/magic6/magic.pdf"}},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        OCR(**response.json())  # validate format
