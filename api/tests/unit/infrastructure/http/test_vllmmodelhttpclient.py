from copy import deepcopy

import pytest

from api.domain.provider.entities import ProviderCarbonFootprintZone
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model import VllmModelHttpClient
from api.tests.unit.infrastructure.http.factories import FormattedRequestContentFactory, VllmModelsResponseFactory


@pytest.fixture
def vllm_model_http_client():
    return VllmModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="vllm-test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


@pytest.fixture
def vllm_models_request_content(vllm_model_http_client):
    return FormattedRequestContentFactory(models=True, model=vllm_model_http_client.model_name)


@pytest.fixture
def vllm_models_response_data():
    return VllmModelsResponseFactory()


class TestVllmModelHttpClient:
    def test_should_format_response_to_models_format(self, vllm_model_http_client, vllm_models_request_content, vllm_models_response_data):
        request_content = vllm_models_request_content.model_copy(deep=True)
        response_data = deepcopy(vllm_models_response_data)

        result = vllm_model_http_client.format_response_to_models_response(request_content=request_content, response_data=response_data)

        assert result == ModelsResponse(
            data=[
                ModelResponse(
                    object="model",
                    type=None,
                    aliases=[],
                    id=vllm_models_response_data["data"][0]["id"],
                    created=vllm_models_response_data["data"][0]["created"],
                    owned_by=vllm_models_response_data["data"][0]["owned_by"],
                    max_context_length=vllm_models_response_data["data"][0]["max_model_len"],
                )
            ]
        )
