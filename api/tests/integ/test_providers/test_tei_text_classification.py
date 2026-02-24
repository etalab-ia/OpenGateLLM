import datetime as dt

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import ProviderType
from api.schemas.models import ModelType
from api.schemas.rerank import Reranks
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
def setup_tei_test_classification(client: TestClient):
    test_id = generate_test_id(prefix="TestUsage")
    process = run_openmockllm(test_id=test_id, backend="tei")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.TEXT_CLASSIFICATION, client=client)
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


@pytest.mark.usefixtures("client", "setup_tei_test_classification")
class TestTeiTextClassification:
    def test_tei_rerank_successful(self, client: TestClient, setup_tei_test_classification: tuple[str, str]):
        """Test successful Rerank processing."""
        key, model_name = setup_tei_test_classification

        response = client.post(
            url=f"/v1{EndpointRoute.RERANK}",
            json={
                "model": model_name,
                "query": "The sun is shining.",
                "documents": ["The document is about the weather.", "The document is about the news.", "The document is about the sports."],
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["results"]) == 3
        Reranks(**response.json())  # validate format

    def test_tei_rerank_with_unknown_model(self, client: TestClient, setup_tei_test_classification: tuple[str, str]):
        """Test the POST /rerank with an unknown model."""
        key, model_name = setup_tei_test_classification

        response = client.post(
            url=f"/v1{EndpointRoute.RERANK}",
            json={
                "model": "unknown",
                "query": "The sun is shining.",
                "documents": ["The document is about the weather.", "The document is about the news.", "The document is about the sports."],
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 404, response.text

    def test_rerank_with_rerank_model_with_top_n(self, client: TestClient, setup_tei_test_classification: tuple[str, str]):
        """Test the POST /rerank with the top_n parameter."""
        key, model_name = setup_tei_test_classification

        response = client.post(
            url=f"/v1{EndpointRoute.RERANK}",
            json={
                "model": model_name,
                "query": "The sun is shining.",
                "documents": ["Sentence 1", "Sentence 2", "Sentence 3", "Sentence 4", "Sentence 5", "Sentence 6"],
                "top_n": 2,
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["results"]) == 2

        Reranks(**response.json())  # test output format

    def test_rerank_with_rerank_model_with_higher_top_n(self, client: TestClient, setup_tei_test_classification: tuple[str, str]):
        """Test the POST /rerank with a higher top_n parameter than the number of documents."""
        key, model_name = setup_tei_test_classification

        response = client.post(
            url=f"/v1{EndpointRoute.RERANK}",
            json={
                "model": model_name,
                "query": "The sun is shining.",
                "documents": ["The document is about the weather.", "The document is about the news.", "The document is about the sports."],
                "top_n": 15,
            },
            headers={"Authorization": f"Bearer {key}"},
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["results"]) == 3

        Reranks(**response.json())  # test output format
