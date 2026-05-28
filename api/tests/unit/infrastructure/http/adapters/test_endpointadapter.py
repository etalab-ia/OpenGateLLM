from http import HTTPMethod
from unittest.mock import Mock, patch

from pydantic import BaseModel
import pytest

from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
    ProviderType,
    ResponseMetrics,
)
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.domain.rerank.entities import CreateRerankBody, Rerank
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.infrastructure.http.adapters._endpointadapter import EndpointAdapter
from api.schemas.admin.providers import ProviderCarbonFootprintZone
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


class _DummyAdapter(EndpointAdapter):
    SOURCE_ENDPOINT = EndpointRoute.RERANK
    TARGET_ENDPOINT_ROUTE = "/v1/dummy"
    TARGET_ENDPOINT_METHOD = HTTPMethod.POST
    REQUEST_TYPE = CreateRerankBody
    RESPONSE_TYPE = Rerank


@pytest.fixture
def provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://provider.test", model_name="test-model", model_total_params=10, model_active_params=5)


@pytest.fixture
def adapter(provider):
    adapter = _DummyAdapter(
        cost_completion_tokens=2.0,
        cost_prompt_tokens=1.0,
        provider=provider,
        model_environmental_impacts_computer=Mock(),
        model_tokenizer=Mock(),
    )
    adapter.model_tokenizer.encode = Mock(return_value=[100, 200])
    adapter.model_environmental_impacts_computer.compute = Mock(return_value=EnvironmentalImpacts(kgCO2eq=1, kWh=2))

    return adapter


class TestEndpointAdapter:
    def test_format_request_adds_model_if_missing(self, adapter):
        # Arrange
        original_request = ProviderOriginalRequest(endpoint=EndpointRoute.RERANK, body=None, form=None, files=None)
        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert isinstance(result, ProviderFormattedRequest)
        assert result.method == HTTPMethod.POST
        assert result.url == "https://provider.test/v1/dummy"
        assert result.body == {"model": "test-model"}
        assert result.form == {}
        assert result.files == {}

    def test_format_request_keeps_model_if_present(self, adapter):
        # Arrange
        original_request = ProviderOriginalRequest(
            endpoint=EndpointRoute.RERANK,
            body=CreateRerankBody(model="keep-me", query="q", documents=["d1", "d2"], top_n=2),
            form=None,
            files=None,
        )
        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert isinstance(result, ProviderFormattedRequest)
        assert result.method == HTTPMethod.POST
        assert result.url == "https://provider.test/v1/dummy"
        assert result.body == {"model": "keep-me", "query": "q", "documents": ["d1", "d2"], "top_n": 2}
        assert result.form == {}
        assert result.files == {}
        assert result.body["model"] == "keep-me"

    def test_format_response_returns_validation_error_on_bad_data(self, adapter):
        class _InvalidResponsePayload(BaseModel):
            id: int

        adapter.RESPONSE_TYPE = _InvalidResponsePayload
        original_request = ProviderOriginalRequest(
            endpoint=EndpointRoute.RERANK,
            body=CreateRerankBody(model="m", query="q", documents=["d"], top_n=1),
        )
        original_response = ProviderOriginalResponse(data={"id": "req-1"}, metrics=ResponseMetrics(latency=10))

        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=0)

        assert result.provider_type == adapter.provider.type
        assert isinstance(result, ProviderAdapterValidationResponseError)
        assert len(result.errors) == 1

    def test_format_response_correctly(self, adapter):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        mock_usage = Usage(prompt_tokens=3, completion_tokens=0, total_tokens=3, cost=0.0003, impacts=EnvironmentalImpacts(kgCO2eq=0.1, kWh=10.0))
        adapter._compute_usage = Mock(return_value=mock_usage)
        original_request = ProviderOriginalRequest(
            endpoint=EndpointRoute.RERANK,
            body=CreateRerankBody(model="m", query="q", documents=["a b c"], top_n=1),
        )
        original_response = ProviderOriginalResponse(
            data={"id": "req-123", "model": "ignored", "results": [{"index": 0, "relevance_score": 0.5}]},
            metrics=ResponseMetrics(latency=10),
        )

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=3)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert result.metrics == ResponseMetrics(latency=10)
        assert result.data.id == "req-123"
        assert result.data.model == "m"
        assert result.data.usage == Usage(
            prompt_tokens=3,
            completion_tokens=0,
            total_tokens=3,
            cost=0.0003,
            impacts=EnvironmentalImpacts(kgCO2eq=0.1, kWh=10.0),
        )

    def test_compute_usage_when_environmental_impacts_computer_is_present(self, adapter):
        # Arrange
        adapter.compute_completion_tokens = Mock(return_value=10)

        adapter._compute_request_cost = Mock(return_value=0.0003)
        formatted_response = ProviderFormattedResponse(
            data=Rerank(id="req-123", model="m", results=[{"index": 0, "relevance_score": 0.5}]),
            metrics=ResponseMetrics(latency=20),
        )
        prompt_tokens = 3

        # Act
        result = adapter._compute_usage(formatted_response=formatted_response, prompt_tokens=prompt_tokens)

        # Assert
        adapter.model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=5,
            model_total_params=10,
            model_zone=ProviderCarbonFootprintZone.WOR,
            completion_tokens=10,
            request_latency=20,
        )
        assert result == Usage(
            prompt_tokens=3,
            completion_tokens=10,
            total_tokens=13,
            cost=0.0003,
            impacts=EnvironmentalImpacts(kgCO2eq=1, kWh=2),
        )

    def test_compute_usage_when_environmental_impacts_computer_is_not_present(self, adapter):
        # Arrange
        adapter.model_environmental_impacts_computer = None
        adapter.compute_completion_tokens = Mock(return_value=10)
        adapter._compute_request_cost = Mock(return_value=0.0003)
        formatted_response = ProviderFormattedResponse(
            data=Rerank(id="req-123", model="m", results=[{"index": 0, "relevance_score": 0.5}]),
            metrics=ResponseMetrics(latency=20),
        )
        prompt_tokens = 3

        # Act
        result = adapter._compute_usage(formatted_response=formatted_response, prompt_tokens=prompt_tokens)

        # Assert
        assert result == Usage(
            prompt_tokens=3,
            completion_tokens=10,
            total_tokens=13,
            cost=0.0003,
            impacts=EnvironmentalImpacts(kgCO2eq=0, kWh=0),
        )

    def test_compute_prompt_when_tokenizer_is_present(self, adapter):
        # Arrange
        body = CreateRerankBody(model="m", query="q", documents=["d1"], top_n=None)
        body.get_prompts = Mock(return_value=["q", "d1 "])
        original_request = ProviderOriginalRequest(endpoint=EndpointRoute.RERANK, body=body)

        # Act
        result = adapter.compute_prompt_tokens(original_request)

        # Assert
        assert result == 2
        adapter.model_tokenizer.encode.assert_called_once_with("q d1")

    def test_compute_prompt_returns_zero_when_tokenizer_is_not_present(self, adapter):
        # Arrange
        adapter.model_tokenizer = None
        body = CreateRerankBody(model="m", query="q", documents=["d1"], top_n=None)
        body.get_prompts = Mock(side_effect=AssertionError("get_prompts should not be executed without tokenizer"))
        original_request = ProviderOriginalRequest(endpoint=EndpointRoute.RERANK, body=body)

        # Act
        result = adapter.compute_prompt_tokens(original_request)

        # Assert
        assert result == 0
        body.get_prompts.assert_not_called()

    # @TODO: add after implement /v1/chat/completions clean architecture refactoring
    # def test_compute_completion_tokens_returns_zero_without_tokenizer(self, provider):
    #     # Arrange
    #     adapter = _DummyAdapter(cost_completion_tokens=0, cost_prompt_tokens=0, provider=provider, model_tokenizer=None)
    #     formatted_response = ProviderFormattedResponse(data=None)

    #     # Act
    #     result = adapter.compute_completion_tokens(formatted_response=formatted_response)
    #     assert result == 0
    #     adapter.RESPONSE_TYPE.get_completions.assert_not_called()

    def test_compute_request_cost_correctly(self):
        # Arrange
        prompt_tokens = 100
        completion_tokens = 100
        cost_prompt_tokens = 1.0
        cost_completion_tokens = 2.0

        # Act
        result = EndpointAdapter._compute_request_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
        )

        # Assert
        assert result == 0.0003

    def test_build_target_url_without_trailing_slash(self):
        # Arrange
        base_url = "https://provider.test"
        target_endpoint_route = "/v1/models"

        # Act
        result = EndpointAdapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/v1/models"

    def test_build_target_url_with_trailing_slash(self):
        # Arrange
        base_url = "https://provider.test/"
        target_endpoint_route = "/v1/models"

        # Act
        result = EndpointAdapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/v1/models"

    def test_build_target_url_with_none_endpoint_route(self):
        # Arrange
        base_url = "https://provider.test/"
        target_endpoint_route = None

        # Act
        result = EndpointAdapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/"

    def test_build_target_url_with_subdomain(self):
        # Arrange
        base_url = "https://provider.test/provider"
        target_endpoint_route = "/v1/models"

        # Act
        result = EndpointAdapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/provider/v1/models"

    def test_extract_request_id_with_id(self):
        # Arrange
        original_response = ProviderOriginalResponse(data={"id": "abc"}, metrics=ResponseMetrics(latency=0))

        # Act
        result = EndpointAdapter._extract_request_id(original_response)

        # Assert
        assert result == "abc"

    def test_extract_request_id_without_id(self):
        # Arrange
        original_response = ProviderOriginalResponse(data={}, metrics=ResponseMetrics(latency=0))

        # Act
        with patch("api.infrastructure.http.adapters._endpointadapter.uuid4", return_value="123-456-789"):
            result = EndpointAdapter._extract_request_id(original_response)

        # Assert
        assert result == "request-123456789"
