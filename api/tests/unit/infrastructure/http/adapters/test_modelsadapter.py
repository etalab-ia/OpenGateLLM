from http import HTTPMethod
from unittest.mock import Mock

import pytest

from api.domain.model.entities import ModelCosts, Models, ModelType
from api.domain.provider.entities import (
    ProviderFormattedResponse,
    ProviderOriginalResponse,
    ProviderType,
)
from api.infrastructure.http.adapters.models.albert import AlbertModelsAdapter
from api.infrastructure.http.adapters.models.mistral import MistralModelsAdapter
from api.infrastructure.http.adapters.models.openai import OpenaiModelsAdapter
from api.infrastructure.http.adapters.models.tei import TeiModelsAdapter
from api.infrastructure.http.adapters.models.vllm import VllmModelsAdapter
from api.tests.integration.factories.albert import AlbertModelsResponseFactory
from api.tests.integration.factories.mistral import MistralModelsResponseFactory
from api.tests.integration.factories.openai import OpenaiModelsResponseFactory
from api.tests.integration.factories.tei import TeiModelsResponseFactory
from api.tests.integration.factories.vllm import VllmModelsResponseFactory
from api.tests.unit.infrastructure.factories import ProviderOriginalRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def albert_provider():
    return ProviderFactory(
        type=ProviderType.ALBERT, url="https://albert.test", model_name="test-albert-model", model_total_params=10, model_active_params=5
    )


@pytest.fixture
def mistral_provider():
    return ProviderFactory(
        type=ProviderType.MISTRAL, url="https://mistral.test", model_name="test-mistral-model", model_total_params=10, model_active_params=5
    )


@pytest.fixture
def openai_provider():
    return ProviderFactory(
        type=ProviderType.OPENAI, url="https://openai.test", model_name="test-openai-model", model_total_params=10, model_active_params=5
    )


@pytest.fixture
def tei_provider():
    return ProviderFactory(type=ProviderType.TEI, url="https://tei.test", model_name="test-tei-model", model_total_params=10, model_active_params=5)


@pytest.fixture
def vllm_provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="test-vllm-model", model_total_params=10, model_active_params=5)  # fmt: off


@pytest.fixture
def albert_models_adapter(albert_provider) -> AlbertModelsAdapter:
    return AlbertModelsAdapter(provider=albert_provider)


@pytest.fixture
def mistral_models_adapter(mistral_provider) -> MistralModelsAdapter:
    return MistralModelsAdapter(provider=mistral_provider)


@pytest.fixture
def openai_models_adapter(openai_provider) -> OpenaiModelsAdapter:
    return OpenaiModelsAdapter(provider=openai_provider)


@pytest.fixture
def tei_models_adapter(tei_provider) -> TeiModelsAdapter:
    return TeiModelsAdapter(provider=tei_provider)


@pytest.fixture
def vllm_models_adapter(vllm_provider) -> VllmModelsAdapter:
    return VllmModelsAdapter(provider=vllm_provider)


@pytest.fixture
def adapter(request):
    return request.getfixturevalue(request.param)


class TestModelsAdapter:
    @pytest.mark.parametrize(
        argnames=("adapter", "target_endpoint_route"),
        argvalues=[
            ("albert_models_adapter", "/v1/models"),
            ("mistral_models_adapter", "/v1/models"),
            ("openai_models_adapter", "/v1/models"),
            ("tei_models_adapter", "/info"),
            ("vllm_models_adapter", "/v1/models"),
        ],
        indirect=["adapter"],
    )
    def test_adapter_have_correct_target_endpoint_route(self, adapter, target_endpoint_route):
        # Assert
        assert adapter.TARGET_ENDPOINT_ROUTE == target_endpoint_route

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["albert_models_adapter", "mistral_models_adapter", "openai_models_adapter", "tei_models_adapter", "vllm_models_adapter"],
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
        argvalues=["albert_models_adapter", "mistral_models_adapter", "openai_models_adapter", "tei_models_adapter", "vllm_models_adapter"],
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
        argvalues=["albert_models_adapter", "mistral_models_adapter", "openai_models_adapter", "tei_models_adapter", "vllm_models_adapter"],
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
        argvalues=["albert_models_adapter", "mistral_models_adapter", "openai_models_adapter", "tei_models_adapter", "vllm_models_adapter"],
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
        argvalues=[
            ("albert_models_adapter", HTTPMethod.GET),
            ("mistral_models_adapter", HTTPMethod.GET),
            ("openai_models_adapter", HTTPMethod.GET),
            ("tei_models_adapter", HTTPMethod.GET),
            ("vllm_models_adapter", HTTPMethod.GET),
        ],
        indirect=["adapter"],
    )
    def test_format_request_return_correct_method(self, adapter, method):
        # Arrange
        original_request = ProviderOriginalRequestFactory(models=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.method == method

    @pytest.mark.parametrize(
        argnames=("adapter", "url"),
        argvalues=[
            ("albert_models_adapter", "https://albert.test/v1/models"),
            ("mistral_models_adapter", "https://mistral.test/v1/models"),
            ("openai_models_adapter", "https://openai.test/v1/models"),
            ("tei_models_adapter", "https://tei.test/info"),
            ("vllm_models_adapter", "https://vllm.test/v1/models"),
        ],
        indirect=["adapter"],
    )
    def test_format_request_return_correct_url(self, adapter, url):
        # Arrange
        original_request = ProviderOriginalRequestFactory(models=True)

        # Act
        result = adapter.format_request(original_request)

        # Assert
        assert result.url == url

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("albert_models_adapter", AlbertModelsResponseFactory()),
            ("mistral_models_adapter", MistralModelsResponseFactory()),
            ("openai_models_adapter", OpenaiModelsResponseFactory()),
            ("tei_models_adapter", TeiModelsResponseFactory()),
            ("vllm_models_adapter", VllmModelsResponseFactory()),
        ],
        indirect=["adapter"],
    )
    def test_format_response_has_no_usage(self, adapter, response_data):
        # Arrange
        original_response = ProviderOriginalResponse(data=response_data)
        original_request = ProviderOriginalRequestFactory(models=True)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert getattr(result.data, "usage", "not found") == "not found"

    def test_format_response_correctly_when_provider_is_albert(self, albert_models_adapter: AlbertModelsAdapter):
        # Arrange
        response_data = AlbertModelsResponseFactory(count=3)
        original_request = ProviderOriginalRequestFactory(models=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = albert_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert len(result.data.data) == 3
        assert result.data.data[0].id == response_data["data"][0]["id"]
        assert result.data.data[0].type is ModelType.TEXT_GENERATION
        assert result.data.data[0].max_context_length == response_data["data"][0]["max_context_length"]
        assert result.data.data[0].aliases == []
        assert result.data.data[0].costs == ModelCosts(prompt_tokens=0, completion_tokens=0)

    def test_format_response_correctly_when_provider_is_openai(self, openai_models_adapter: OpenaiModelsAdapter):
        # Arrange
        response_data = OpenaiModelsResponseFactory(count=3)
        original_request = ProviderOriginalRequestFactory(models=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = openai_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert len(result.data.data) == 3
        assert result.data.data[0].id == response_data["data"][0]["id"]
        assert result.data.data[0].type is ModelType.TEXT_GENERATION
        assert result.data.data[0].owned_by == response_data["data"][0]["owned_by"]
        assert result.data.data[0].max_context_length is None
        assert result.data.data[0].aliases == []
        assert result.data.data[0].costs == ModelCosts(prompt_tokens=0, completion_tokens=0)

    def test_format_response_correctly_when_provider_is_mistral(self, mistral_models_adapter: MistralModelsAdapter):
        # Arrange
        response_data = MistralModelsResponseFactory(count=3)
        original_request = ProviderOriginalRequestFactory(models=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = mistral_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert len(result.data.data) == 3
        assert result.data.data[0].id == response_data["data"][0]["id"]
        assert result.data.data[0].type is ModelType.TEXT_GENERATION
        assert result.data.data[0].max_context_length == response_data["data"][0]["max_context_length"]
        assert result.data.data[0].owned_by == response_data["data"][0]["owned_by"]
        assert result.data.data[0].aliases == []
        assert result.data.data[0].costs == ModelCosts(prompt_tokens=0, completion_tokens=0)

    def test_format_response_correctly_when_provider_is_tei(self, tei_models_adapter: TeiModelsAdapter):
        # Arrange
        response_data = TeiModelsResponseFactory(count=1)
        original_request = ProviderOriginalRequestFactory(models=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = tei_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert len(result.data.data) == 1
        assert result.data.data[0].id == response_data["model_id"]
        assert result.data.data[0].type is ModelType.TEXT_GENERATION
        assert result.data.data[0].max_context_length == response_data["max_input_length"]
        assert result.data.data[0].owned_by == "tei"
        assert result.data.data[0].aliases == []
        assert result.data.data[0].costs == ModelCosts(prompt_tokens=0, completion_tokens=0)

    def test_format_response_correctly_when_provider_is_vllm(self, vllm_models_adapter: VllmModelsAdapter):
        # Arrange
        response_data = VllmModelsResponseFactory(count=1)
        original_request = ProviderOriginalRequestFactory(models=True)
        original_response = ProviderOriginalResponse(data=response_data)

        # Act
        result = vllm_models_adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert len(result.data.data) == 1
        assert result.data.data[0].id == response_data["data"][0]["id"]
        assert result.data.data[0].type is ModelType.TEXT_GENERATION
        assert result.data.data[0].max_context_length == response_data["data"][0]["max_model_len"]
        assert result.data.data[0].owned_by == response_data["data"][0]["owned_by"]
        assert result.data.data[0].aliases == []
        assert result.data.data[0].costs == ModelCosts(prompt_tokens=0, completion_tokens=0)

    @pytest.mark.parametrize(
        argnames=("adapter", "response_data"),
        argvalues=[
            ("albert_models_adapter", AlbertModelsResponseFactory()),
            ("mistral_models_adapter", MistralModelsResponseFactory()),
            ("openai_models_adapter", OpenaiModelsResponseFactory()),
            ("tei_models_adapter", TeiModelsResponseFactory()),
            ("vllm_models_adapter", VllmModelsResponseFactory()),
        ],
        indirect=["adapter"],
    )
    def test_format_response_extract_request_id_not_called(self, adapter, response_data):
        # Arrange
        adapter._extract_request_id = Mock()
        original_response = ProviderOriginalResponse(data=response_data)
        original_request = ProviderOriginalRequestFactory(models=True)

        # Act
        result = adapter.format_response(original_response=original_response, original_request=original_request)

        # Assert
        assert isinstance(result, ProviderFormattedResponse)
        assert isinstance(result.data, Models)
        assert getattr(result.data, "id", "not found") == "not found"
        adapter._extract_request_id.assert_not_called()

    @pytest.mark.parametrize(
        argnames=("adapter"),
        argvalues=["albert_models_adapter", "mistral_models_adapter", "openai_models_adapter", "tei_models_adapter", "vllm_models_adapter"],
        indirect=["adapter"],
    )
    def test_source_endpoint_is_models(self, adapter):
        # Assert
        assert adapter.SOURCE_ENDPOINT == EndpointRoute.MODELS
