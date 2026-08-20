from http import HTTPMethod
from unittest.mock import Mock

import pytest

from api.domain.provider.entities import BasicAuth, ProviderFormattedResponse, ProviderMetrics, ProviderOriginalResponse, ProviderType
from api.domain.provider.errors import ProviderAdapterValidationResponseError
from api.infrastructure.http.adapters.metrics.mistral import MistralMetricsAdapter
from api.infrastructure.http.adapters.metrics.vllm import VllmMetricsAdapter
from api.tests.integration.factories.mistral import MistralMetricsResponseFactory
from api.tests.integration.factories.vllm import VllmMetricsResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


def build_metrics_text(model_name: str, running: float = 0.0, waiting: float = 0.0) -> str:
    return f'vllm:num_requests_running{{model_name="{model_name}"}} {running}\nvllm:num_requests_waiting{{model_name="{model_name}"}} {waiting}\n'


@pytest.fixture
def vllm_provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="test-vllm-model", model_total_params=10, model_active_params=5)  # fmt: off


@pytest.fixture
def mistral_provider():
    return ProviderFactory(
        type=ProviderType.MISTRAL,
        url="https://mistral.test",
        model_name="test-mistral-model",
        basic_auth=BasicAuth(username="metrics", password="secret"),
        model_total_params=10,
        model_active_params=5,
    )


@pytest.fixture
def mistral_provider_without_auth():
    return ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test", model_name="test-mistral-model", model_total_params=10, model_active_params=5)  # fmt: off


@pytest.fixture
def vllm_metrics_adapter(vllm_provider) -> VllmMetricsAdapter:
    return VllmMetricsAdapter(provider=vllm_provider)


@pytest.fixture
def mistral_metrics_adapter(mistral_provider) -> MistralMetricsAdapter:
    return MistralMetricsAdapter(provider=mistral_provider)


@pytest.fixture
def mistral_metrics_adapter_without_auth(mistral_provider_without_auth) -> MistralMetricsAdapter:
    return MistralMetricsAdapter(provider=mistral_provider_without_auth)


@pytest.fixture
def adapter(request):
    return request.getfixturevalue(request.param)


class TestMetricsAdapter:
    @pytest.mark.parametrize(
        argnames=("adapter", "target_endpoint_route"),
        argvalues=[("vllm_metrics_adapter", "/metrics"), ("mistral_metrics_adapter", "/metrics")],
        indirect=["adapter"],
    )
    def test_adapter_have_correct_target_endpoint_route(self, adapter, target_endpoint_route):
        # Assert
        assert adapter.TARGET_ENDPOINT_ROUTE == target_endpoint_route

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["vllm_metrics_adapter", "mistral_metrics_adapter"],
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
        argvalues=["vllm_metrics_adapter", "mistral_metrics_adapter"],
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
        argvalues=["vllm_metrics_adapter", "mistral_metrics_adapter"],
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
        argvalues=["vllm_metrics_adapter", "mistral_metrics_adapter"],
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
        argnames=("adapter", "method"),
        argvalues=[("vllm_metrics_adapter", HTTPMethod.GET), ("mistral_metrics_adapter", HTTPMethod.GET)],
        indirect=["adapter"],
    )
    def test_format_request_return_correct_method(self, adapter, method):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.method == method

    @pytest.mark.parametrize(
        argnames=("adapter", "url"),
        argvalues=[
            ("vllm_metrics_adapter", "https://vllm.test/metrics"),
            ("mistral_metrics_adapter", "https://mistral.test/metrics"),
        ],
        indirect=["adapter"],
    )
    def test_format_request_return_correct_url(self, adapter, url):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.url == url

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("mistral_metrics_adapter", MistralMetricsResponseFactory()),
            ("vllm_metrics_adapter", VllmMetricsResponseFactory()),
        ],
        indirect=["adapter"],
    )
    def test_format_response_has_no_usage(self, adapter, response_data):
        # Arrange
        original_response = ProviderOriginalResponse(text=response_data["text"])
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, ProviderMetrics)
        assert getattr(result.data, "usage", "not found") == "not found"

    def test_format_request_has_no_auth(self, vllm_metrics_adapter: VllmMetricsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = vllm_metrics_adapter.format_request(original_request)

        # Assert
        assert result.auth is None

    def test_format_request_includes_provider_basic_auth(self, mistral_metrics_adapter: MistralMetricsAdapter, mistral_provider):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = mistral_metrics_adapter.format_request(original_request)

        # Assert
        assert result.auth == mistral_provider.basic_auth

    def test_format_request_has_no_auth_when_provider_has_none(self, mistral_metrics_adapter_without_auth: MistralMetricsAdapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = mistral_metrics_adapter_without_auth.format_request(original_request)

        # Assert
        assert result.auth is None

    @pytest.mark.parametrize(
        argnames=("adapter", "model_name", "running", "waiting"),
        argvalues=[
            ("vllm_metrics_adapter", "test-vllm-model", 3.0, 7.0),
            ("mistral_metrics_adapter", "test-mistral-model", 3.0, 7.0),
        ],
        indirect=["adapter"],
    )
    def test_format_response_parses_prometheus_text(self, adapter, model_name, running, waiting):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)
        original_response = ProviderOriginalResponse(text=build_metrics_text(model_name=model_name, running=running, waiting=waiting))

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, ProviderMetrics)
        assert result.data.running_requests == running
        assert result.data.waiting_requests == waiting

    @pytest.mark.parametrize(
        argnames=("adapter", "model_name"),
        argvalues=[
            ("vllm_metrics_adapter", "test-vllm-model"),
            ("mistral_metrics_adapter", "test-mistral-model"),
        ],
        indirect=["adapter"],
    )
    def test_format_response_sums_samples_for_same_model(self, adapter, model_name):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)
        original_response = ProviderOriginalResponse(
            text=(
                f'vllm:num_requests_running{{model_name="{model_name}"}} 2.0\n'
                f'vllm:num_requests_running{{model_name="{model_name}"}} 3.0\n'
                f'vllm:num_requests_waiting{{model_name="{model_name}"}} 1.0\n'
                f'vllm:num_requests_waiting{{model_name="{model_name}"}} 4.0\n'
                f'vllm:num_requests_running{{model_name="other-model"}} 99.0\n'
                f'vllm:num_requests_waiting{{model_name="other-model"}} 88.0\n'
            )
        )

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert result.data.running_requests == 5.0
        assert result.data.waiting_requests == 5.0

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["vllm_metrics_adapter", "mistral_metrics_adapter"],
        indirect=["adapter"],
    )
    def test_format_response_returns_validation_error_on_invalid_text(self, adapter):
        # Arrange
        original_request = ProviderOriginalRequestFactory(metrics=True)
        original_response = ProviderOriginalResponse(text="not valid prometheus text")

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderAdapterValidationResponseError)
        assert result.provider_type == adapter.provider.type
        assert len(result.errors) == 1

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("mistral_metrics_adapter", MistralMetricsResponseFactory()),
            ("vllm_metrics_adapter", VllmMetricsResponseFactory()),
        ],
        indirect=["adapter"],
    )
    def test_format_response_extracts_request_id(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock(return_value="req-123")
        original_response = ProviderOriginalResponse(text=response_data["text"])
        original_request = ProviderOriginalRequestFactory(metrics=True)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, ProviderMetrics)
        assert result.id == "req-123"
        assert getattr(result.data, "id", "not found") == "not found"
        adapter._extract_request_id.assert_called_once_with(original_response=original_response)

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["vllm_metrics_adapter", "mistral_metrics_adapter"],
        indirect=["adapter"],
    )
    def test_source_endpoint_is_metrics(self, adapter):
        # Assert
        assert adapter.SOURCE_ENDPOINT == EndpointRoute.METRICS
