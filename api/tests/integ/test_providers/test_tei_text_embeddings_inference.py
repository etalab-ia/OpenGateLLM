import datetime as dt

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import ProviderType
from api.schemas.embeddings import Embeddings
from api.schemas.models import ModelType
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
from api.utils.variables import ENDPOINT__EMBEDDINGS


@pytest.fixture(scope="module")
def setup_tei_test_embeddings_inference(client: TestClient):
    test_id = generate_test_id(prefix="TestUsage")
    process = run_openmockllm(test_id=test_id, backend="tei")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.TEXT_EMBEDDINGS_INFERENCE, client=client)
        create_provider(
            router_id=router_id,
            provider_url=process.url,
            provider_key=None,
            provider_name=process.model_name,
            provider_type=ProviderType.TEI,
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
        pass


@pytest.mark.usefixtures("client", "setup_tei_test_embeddings_inference")
class TestTeiTextEmbeddingsInference:
    def test_tei_embeddings_successful(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test successful embeddings processing."""

        key, model_name = setup_tei_test_embeddings_inference

        response = client.post(
            f"/v1{ENDPOINT__EMBEDDINGS}",
            json={
                "model": model_name,
                "input": "Hello, this is a test.",
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        Embeddings(**response.json())  # validate format

    def test_tei_embeddings_token_integers_input(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with token integers input."""
        key, model_name = setup_tei_test_embeddings_inference

        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": model_name, "input": [1, 2, 3, 4, 5]},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text

    def test_tei_embeddings_token_integers_batch_input(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with batch of token integers input."""
        key, model_name = setup_tei_test_embeddings_inference
        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": model_name, "input": [[1, 2, 3], [4, 5, 6]]},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        Embeddings(**response.json())  # validate format

    def test_tei_embeddings_invalid_encoding_format(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with invalid encoding format."""
        key, model_name = setup_tei_test_embeddings_inference
        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": model_name, "input": "Test text", "encoding_format": "invalid_format"},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 422, response.text

    def test_tei_embeddings_batch_input(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with batch input."""
        key, model_name = setup_tei_test_embeddings_inference
        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": model_name, "input": ["Hello, this is a test.", "This is another test."]},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        Embeddings(**response.json())  # validate format
        assert len(response.json()["data"]) == 2

    def test_tei_embeddings_empty_input(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with empty input."""
        key, model_name = setup_tei_test_embeddings_inference
        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": model_name, "input": ""},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 422, response.text

    def test_tei_embeddings_invalid_model(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with invalid model."""
        key, model_name = setup_tei_test_embeddings_inference
        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": "invalid_model_id", "input": "Hello, this is a test."},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 404, response.text

    def test_tei_embeddings_missing_input(self, client: TestClient, setup_tei_test_embeddings_inference: tuple[str, str]):
        """Test the POST /embeddings endpoint with missing input."""
        key, model_name = setup_tei_test_embeddings_inference
        response = client.post(
            url=f"/v1{ENDPOINT__EMBEDDINGS}",
            json={"model": model_name},
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 422, response.text
