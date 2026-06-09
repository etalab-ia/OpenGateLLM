from http import HTTPMethod
from unittest.mock import Mock, patch

from pydantic import BaseModel
import pytest

from api.domain.provider.entities import HostingZone, ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.domain.rerank.entities import Rerank
from api.domain.usage.entities import EnvironmentalImpacts, Usage
from api.infrastructure.http.adapters.rerank.tei import TeiRerankAdapter
from api.infrastructure.http.adapters.rerank.vllm import VllmRerankAdapter
from api.tests.integration.factories.tei import TeiRerankResponseFactory
from api.tests.integration.factories.vllm import VllmRerankResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory, ProviderRerankFormattedResponseFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def tei_provider():
    return ProviderFactory(type=ProviderType.TEI, url="https://tei.test", model_name="test-tei-model", model_total_params=10, model_active_params=5)


@pytest.fixture
def vllm_provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="test-vllm-model", model_total_params=10, model_active_params=5)  # fmt: off


@pytest.fixture
def model_tokenizer():
    return Mock()


@pytest.fixture
def model_environmental_impacts_computer():
    return Mock()


@pytest.fixture
def tei_rerank_adapter(tei_provider, model_tokenizer, model_environmental_impacts_computer) -> TeiRerankAdapter:
    adapter = TeiRerankAdapter(
        cost_completion_tokens=0,
        cost_prompt_tokens=0,
        provider=tei_provider,
        model_tokenizer=model_tokenizer,
        model_environmental_impacts_computer=model_environmental_impacts_computer,
    )
    adapter.model_tokenizer.encode = Mock(return_value=[100, 200])
    adapter.model_environmental_impacts_computer.compute = Mock(return_value=EnvironmentalImpacts(kgCO2eq=1, kWh=2))

    return adapter


@pytest.fixture
def vllm_rerank_adapter(vllm_provider, model_tokenizer, model_environmental_impacts_computer) -> VllmRerankAdapter:
    adapter = VllmRerankAdapter(
        cost_completion_tokens=0,
        cost_prompt_tokens=0,
        provider=vllm_provider,
        model_tokenizer=model_tokenizer,
        model_environmental_impacts_computer=model_environmental_impacts_computer,
    )
    adapter.model_tokenizer.encode = Mock(return_value=[100, 200])
    adapter.model_environmental_impacts_computer.compute = Mock(return_value=EnvironmentalImpacts(kgCO2eq=1, kWh=2))

    return adapter


@pytest.fixture
def adapter(request):
    return request.getfixturevalue(request.param)


class TestRerankAdapter:
    @pytest.mark.parametrize(
        argnames=("adapter", "target_endpoint_route"),
        argvalues=[("tei_rerank_adapter", "/rerank"), ("vllm_rerank_adapter", "/v2/rerank")],
        indirect=["adapter"],
    )
    def test_adapter_have_correct_target_endpoint_route(self, adapter, target_endpoint_route):
        # Assert
        assert adapter.TARGET_ENDPOINT_ROUTE == target_endpoint_route

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_build_target_url_with_none_endpoint_route(self, adapter):
        # Arrange
        base_url = "https://provider.test/"
        target_endpoint_route = None

        # Act
        result = adapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_build_target_url_with_subdomain(self, adapter):
        # Arrange
        base_url = "https://provider.test/provider"
        target_endpoint_route = "/v1/endpoint"

        # Act
        result = adapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/provider/v1/endpoint"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_build_target_url_with_trailing_slash(self, adapter):
        # Arrange
        base_url = "https://provider.test/"
        target_endpoint_route = "/v1/endpoint"

        # Act
        result = adapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/v1/endpoint"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_build_target_url_without_trailing_slash(self, adapter):
        # Arrange
        base_url = "https://provider.test"
        target_endpoint_route = "/v1/endpoint"

        # Act
        result = adapter._build_target_url(base_url=base_url, target_endpoint_route=target_endpoint_route)

        # Assert
        assert result == "https://provider.test/v1/endpoint"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_compute_completion_tokens_returns_zero_when_tokenizer_is_not_present(self, adapter):
        # Arrange
        formatted_response = ProviderRerankFormattedResponseFactory()
        adapter.model_tokenizer = None

        # Act
        result = adapter._compute_completion_tokens(formatted_response=formatted_response)

        # Assert
        assert result == 0

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_compute_completion_tokens_returns_zero_when_tokenizer_is_present(self, adapter):
        # Arrange
        formatted_response = ProviderRerankFormattedResponseFactory()

        # Act
        result = adapter._compute_completion_tokens(formatted_response=formatted_response)

        # Assert
        assert result == 0

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_compute_prompt_tokens_returns_zero_when_tokenizer_is_not_present(self, adapter):
        # Arrange
        adapter.model_tokenizer = None
        original_request = ProviderOriginalRequestFactory(rerank=True)

        # Act
        result = adapter.compute_prompt_tokens(original_request)

        # Assert
        assert result == 0

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_compute_prompt_tokens_when_tokenizer_is_present(self, adapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_request.body.query = "query"
        original_request.body.documents = ["document1", "document2 "]

        # Act
        result = adapter.compute_prompt_tokens(original_request)

        # Assert
        assert result == 2
        adapter.model_tokenizer.encode.assert_called_once_with("query document1 document2")

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_compute_request_cost_correctly(self, adapter):
        # Arrange
        prompt_tokens = 100
        completion_tokens = 100
        cost_prompt_tokens = 1.0
        cost_completion_tokens = 2.0

        # Act
        result = adapter._compute_request_cost(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_prompt_tokens=cost_prompt_tokens,
            cost_completion_tokens=cost_completion_tokens,
        )

        # Assert
        assert result == 0.0003

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_compute_usage_when_environmental_impacts_computer_is_not_present(self, adapter):
        # Arrange
        adapter.model_environmental_impacts_computer = None
        adapter._compute_request_cost = Mock(return_value=0.0003)

        # Act
        result = adapter._compute_usage(completion_tokens=10, prompt_tokens=3, latency=20)

        # Assert
        assert result == Usage(
            prompt_tokens=3,
            completion_tokens=10,
            total_tokens=13,
            cost=0.0003,
            impacts=EnvironmentalImpacts(kgCO2eq=0, kWh=0),
        )

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("tei_rerank_adapter", TeiRerankResponseFactory()),
            ("vllm_rerank_adapter", VllmRerankResponseFactory()),
        ],
        indirect=["adapter"],
    )
    def test_compute_usage_when_environmental_impacts_computer_is_present(self, adapter, response_data):
        # Arrange
        adapter._compute_request_cost = Mock(return_value=0.0003)

        # Act
        result = adapter._compute_usage(completion_tokens=0, prompt_tokens=3, latency=20)

        # Assert
        adapter.model_environmental_impacts_computer.compute.assert_called_once_with(
            model_active_params=5,
            model_total_params=10,
            model_zone=HostingZone.WOR,
            completion_tokens=0,
            request_latency=20,
        )
        assert result == Usage(prompt_tokens=3, completion_tokens=0, total_tokens=3, cost=0.0003, impacts=EnvironmentalImpacts(kgCO2eq=1, kWh=2))

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_extract_request_id_with_id(self, adapter):
        # Arrange
        original_response = ProviderOriginalResponse(data={"id": "abc"})

        # Act
        result = adapter._extract_request_id(original_response)

        # Assert
        assert result == "abc"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_extract_request_id_without_id(self, adapter):
        # Arrange
        original_response = ProviderOriginalResponse(data={})

        # Act
        with patch("api.infrastructure.http.adapters._baseadapter.uuid4", return_value="123-456-789"):
            result = adapter._extract_request_id(original_response)

        # Assert
        assert result == "request-123456789"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_format_request_preserve_extra_fields(self, adapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_request.body.extra_field = "extra_value"

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.body["extra_field"] == "extra_value"
        assert "model" in result.body

    @pytest.mark.parametrize(
        argnames=("adapter", "provider_model_name"),
        argvalues=[("vllm_rerank_adapter", "test-vllm-model")],
        indirect=["adapter"],
    )
    def test_format_request_replace_model_by_provider_model_name(self, adapter, provider_model_name):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert isinstance(result, ProviderFormattedRequest)
        assert "model" in result.body
        assert result.body["model"] == provider_model_name

    @pytest.mark.parametrize(
        argnames=("adapter", "method"),
        argvalues=[("tei_rerank_adapter", HTTPMethod.POST), ("vllm_rerank_adapter", HTTPMethod.POST)],
        indirect=["adapter"],
    )
    def test_format_request_return_correct_method(self, adapter, method):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.method == method

    @pytest.mark.parametrize(
        argnames=("adapter", "url"),
        argvalues=[("tei_rerank_adapter", "https://tei.test/rerank"), ("vllm_rerank_adapter", "https://vllm.test/v2/rerank")],
        indirect=["adapter"],
    )
    def test_format_request_return_correct_url(self, adapter, url):
        # Arrange
        original_request = ProviderOriginalRequestFactory(rerank=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.url == url

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("tei_rerank_adapter", TeiRerankResponseFactory(indices=[2, 0, 1], relevance_scores=[0.72, 1, 0.95])),
            ("vllm_rerank_adapter", VllmRerankResponseFactory(indices=[2, 0, 1], relevance_scores=[0.72, 1, 0.95])),
        ],
        indirect=["adapter"],
    )
    def test_format_response_correctly_with_top_n(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        mock_usage = Usage(prompt_tokens=3, completion_tokens=0, total_tokens=3, cost=0.0003, impacts=EnvironmentalImpacts(kgCO2eq=0.1, kWh=10.0))
        adapter._compute_usage = Mock(return_value=mock_usage)
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_request.body.top_n = None
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=3)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Rerank)
        assert len(result.data.results) == 3
        assert result.data.results[0].relevance_score == 1
        assert result.data.results[0].index == 0
        assert result.data.id == "req-123"
        assert result.data.model == "openweight-rerank"
        assert result.data.usage == mock_usage
        adapter._compute_usage.assert_called_once_with(prompt_tokens=3, completion_tokens=0, latency=0)

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("tei_rerank_adapter", TeiRerankResponseFactory(indices=[2, 0, 1], relevance_scores=[0.72, 1, 0.95])),
            ("vllm_rerank_adapter", VllmRerankResponseFactory(indices=[2, 0, 1], relevance_scores=[0.72, 1, 0.95], top_n=2)),
        ],
        indirect=["adapter"],
    )
    def test_format_response_correctly_without_top_n(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        mock_usage = Usage(prompt_tokens=3, completion_tokens=0, total_tokens=3, cost=0.0003, impacts=EnvironmentalImpacts(kgCO2eq=0.1, kWh=10.0))
        adapter._compute_usage = Mock(return_value=mock_usage)
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_request.body.top_n = 2
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=3)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Rerank)
        assert len(result.data.results) == 2
        assert result.data.results[0].relevance_score == 1
        assert result.data.results[0].index == 0
        assert result.data.id == "req-123"
        assert result.data.model == "openweight-rerank"
        assert result.data.usage == mock_usage
        adapter._compute_usage.assert_called_once_with(prompt_tokens=3, completion_tokens=0, latency=0)

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[("vllm_rerank_adapter", VllmRerankResponseFactory(extra_field="extra_value"))],
        indirect=["adapter"],
    )
    def test_format_response_preserve_extra_fields(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        mock_usage = Usage(prompt_tokens=3, completion_tokens=0, total_tokens=3, cost=0.0003, impacts=EnvironmentalImpacts(kgCO2eq=0.1, kWh=10.0))
        adapter._compute_usage = Mock(return_value=mock_usage)
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=0)

        # Assert
        assert result.data.extra_field == "extra_value"

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[("tei_rerank_adapter", TeiRerankResponseFactory(return_text=True, sentences=["document1", "document1"]))],
        indirect=["adapter"],
    )
    def test_format_response_preserve_extra_fields_for_tei(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        mock_usage = Usage(prompt_tokens=3, completion_tokens=0, total_tokens=3, cost=0.0003, impacts=EnvironmentalImpacts(kgCO2eq=0.1, kWh=10.0))
        adapter._compute_usage = Mock(return_value=mock_usage)
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=0)

        # Assert
        assert result.data.results[0].text == "document1"

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[("tei_rerank_adapter", TeiRerankResponseFactory()), ("vllm_rerank_adapter", VllmRerankResponseFactory())],
        indirect=["adapter"],
    )
    def test_format_response_returns_validation_error_on_bad_data(self, adapter, response_data):
        # Arrange
        class _InvalidResponsePayload(BaseModel):
            id: int

        adapter.RESPONSE_TYPE = _InvalidResponsePayload
        original_request = ProviderOriginalRequestFactory(rerank=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request, prompt_tokens=0)

        # Assert
        assert result.provider_type == adapter.provider.type
        assert isinstance(result, ProviderAdapterValidationResponseError)
        assert len(result.errors) == 1

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_source_endpoint_is_rerank(self, adapter):
        # Assert
        assert adapter.SOURCE_ENDPOINT == EndpointRoute.RERANK
