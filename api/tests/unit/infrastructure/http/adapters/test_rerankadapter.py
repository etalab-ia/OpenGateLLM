from http import HTTPMethod
from unittest.mock import Mock, patch

from pydantic import BaseModel
import pytest

from api.domain.provider.entities import ProviderRawResponse, ProviderResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.domain.rerank.entities import Rerank
from api.infrastructure.http import HttpProviderRequest
from api.infrastructure.http.adapters.rerank.tei import TeiRerankAdapter
from api.infrastructure.http.adapters.rerank.vllm import VllmRerankAdapter
from api.tests.integration.factories.tei import TeiRerankResponseFactory
from api.tests.integration.factories.vllm import VllmRerankResponseFactory
from api.tests.unit.infrastructure.factories import ProviderRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def tei_provider():
    return ProviderFactory(type=ProviderType.TEI, url="https://tei.test", model_name="test-tei-model", model_total_params=10, model_active_params=5)


@pytest.fixture
def vllm_provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="test-vllm-model", model_total_params=10, model_active_params=5)  # fmt: off


@pytest.fixture
def tei_rerank_adapter(tei_provider) -> TeiRerankAdapter:
    return TeiRerankAdapter(provider=tei_provider)


@pytest.fixture
def vllm_rerank_adapter(vllm_provider) -> VllmRerankAdapter:
    return VllmRerankAdapter(provider=vllm_provider)


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
    def test_extract_request_id_with_id(self, adapter):
        # Arrange
        original_response = ProviderRawResponse(data={"id": "abc"})

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
        original_response = ProviderRawResponse(data={})

        # Act
        with patch("api.infrastructure.http.adapters._httpprovideradapter.uuid4", return_value="123-456-789"):
            result = adapter._extract_request_id(original_response)

        # Assert
        assert result == "request-123456789"

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_to_http_request_preserve_extra_fields(self, adapter):
        # Arrange
        original_request = ProviderRequestFactory(rerank=True)
        original_request.payload.extra_field = "extra_value"

        # Act
        result = adapter.to_http_request(original_request)

        # Assert
        assert result.body["extra_field"] == "extra_value"
        assert "model" in result.body

    @pytest.mark.parametrize(
        argnames=("adapter", "provider_model_name"),
        argvalues=[("vllm_rerank_adapter", "test-vllm-model")],
        indirect=["adapter"],
    )
    def test_to_http_request_replace_model_by_provider_model_name(self, adapter, provider_model_name):
        # Arrange
        original_request = ProviderRequestFactory(rerank=True)

        # Act
        result = adapter.to_http_request(original_request)

        # Assert
        assert isinstance(result, HttpProviderRequest)
        assert "model" in result.body
        assert result.body["model"] == provider_model_name

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["tei_rerank_adapter", "vllm_rerank_adapter"],
        indirect=["adapter"],
    )
    def test_to_http_request_excludes_none_fields(self, adapter):
        # Arrange
        original_request = ProviderRequestFactory(rerank=True)
        original_request.payload.top_n = None

        # Act
        result = adapter.to_http_request(original_request)

        # Assert
        assert "top_n" not in result.body
        assert "query" in result.body

    @pytest.mark.parametrize(
        argnames=("adapter", "method"),
        argvalues=[("tei_rerank_adapter", HTTPMethod.POST), ("vllm_rerank_adapter", HTTPMethod.POST)],
        indirect=["adapter"],
    )
    def test_to_http_request_return_correct_method(self, adapter, method):
        # Arrange
        original_request = ProviderRequestFactory(rerank=True)

        # Act
        result = adapter.to_http_request(original_request)

        # Assert
        assert result.method == method

    @pytest.mark.parametrize(
        argnames=("adapter", "url"),
        argvalues=[("tei_rerank_adapter", "https://tei.test/rerank"), ("vllm_rerank_adapter", "https://vllm.test/v2/rerank")],
        indirect=["adapter"],
    )
    def test_to_http_request_return_correct_url(self, adapter, url):
        # Arrange
        original_request = ProviderRequestFactory(rerank=True)

        # Act
        result = adapter.to_http_request(original_request)

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
    def test_to_domain_response_correctly_with_top_n(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        original_request = ProviderRequestFactory(rerank=True)
        original_request.payload.top_n = None
        original_response = ProviderRawResponse(data=response_data)

        # Act
        result = adapter.to_domain_response(raw_response=original_response, request=original_request)

        # Assert
        assert isinstance(result, ProviderResponse)
        assert isinstance(result.data, Rerank)
        assert len(result.data.results) == 3
        assert result.data.results[0].relevance_score == 1
        assert result.data.results[0].index == 0
        assert result.data.id == "req-123"
        assert result.data.model == "openweight-rerank"

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("tei_rerank_adapter", TeiRerankResponseFactory(indices=[2, 0, 1], relevance_scores=[0.72, 1, 0.95])),
            ("vllm_rerank_adapter", VllmRerankResponseFactory(indices=[2, 0, 1], relevance_scores=[0.72, 1, 0.95], top_n=2)),
        ],
        indirect=["adapter"],
    )
    def test_to_domain_response_correctly_without_top_n(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        original_request = ProviderRequestFactory(rerank=True)
        original_request.payload.top_n = 2
        original_response = ProviderRawResponse(data=response_data)

        # Act
        result = adapter.to_domain_response(raw_response=original_response, request=original_request)

        # Assert
        assert isinstance(result, ProviderResponse)
        assert isinstance(result.data, Rerank)
        assert len(result.data.results) == 2
        assert result.data.results[0].relevance_score == 1
        assert result.data.results[0].index == 0
        assert result.data.id == "req-123"
        assert result.data.model == "openweight-rerank"

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[("vllm_rerank_adapter", VllmRerankResponseFactory(extra_field="extra_value"))],
        indirect=["adapter"],
    )
    def test_to_domain_response_preserve_extra_fields(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        original_request = ProviderRequestFactory(rerank=True)
        original_response = ProviderRawResponse(data=response_data)

        # Act
        result = adapter.to_domain_response(raw_response=original_response, request=original_request)

        # Assert
        assert result.data.extra_field == "extra_value"

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[("tei_rerank_adapter", TeiRerankResponseFactory(return_text=True, sentences=["document1", "document1"]))],
        indirect=["adapter"],
    )
    def test_to_domain_response_preserve_extra_fields_for_tei(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        original_request = ProviderRequestFactory(rerank=True)
        original_response = ProviderRawResponse(data=response_data)

        # Act
        result = adapter.to_domain_response(raw_response=original_response, request=original_request)

        # Assert
        assert result.data.results[0].text == "document1"

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[("tei_rerank_adapter", TeiRerankResponseFactory()), ("vllm_rerank_adapter", VllmRerankResponseFactory())],
        indirect=["adapter"],
    )
    def test_to_domain_response_returns_validation_error_on_bad_data(self, adapter, response_data):
        # Arrange
        class _InvalidResponsePayload(BaseModel):
            id: int

        adapter.RESPONSE_TYPE = _InvalidResponsePayload
        original_request = ProviderRequestFactory(rerank=True)
        original_response = ProviderRawResponse(data=response_data)

        # Act
        result = adapter.to_domain_response(raw_response=original_response, request=original_request)

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
