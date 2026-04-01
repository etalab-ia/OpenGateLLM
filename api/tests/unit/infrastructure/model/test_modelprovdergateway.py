from http import HTTPMethod
from unittest.mock import AsyncMock, Mock

import factory
import pytest

from api.domain.model import ModelType as RouterType
from api.domain.provider import ProviderCapabilities
from api.domain.provider.entities import ProviderCarbonFootprintZone, ProviderType
from api.domain.provider.errors import ModelProviderNotFoundError, ProviderNotReachableError
from api.infrastructure.http.model import (
    AlbertModelHttpClient,
    FormattedModelRequest,
    MistralModelHttpClient,
    ModelHttpClient,
    ModelHttpExchange,
    OpenaiModelHttpClient,
    OriginalModelRequest,
    TeiModelHttpClient,
    VllmModelHttpClient,
)
from api.infrastructure.model._modelprovidergateway import ModelProviderGateway
from api.tests.unit.infrastructure.http.factories.mistral import MistralOriginalResponseFactory
from api.utils.exceptions import HTTPException, ModelIsTooBusyException
from api.utils.variables import EndpointRoute


class HttpResponseFactory(factory.Factory):
    class Meta:
        model = Mock
        exclude = ("payload",)

    status_code = 200
    payload = factory.LazyFunction(lambda: {})
    json = factory.LazyAttribute(lambda self: Mock(return_value=self.payload))


class ModelPayloadFactory(factory.DictFactory):
    class Meta:
        model = dict

    object = "model"
    id = "test-model"
    type = factory.Faker("random_element", elements=list(ModelType))
    aliases = factory.LazyFunction(list)
    created = factory.LazyFunction(lambda: int(fake.unix_time()))
    owned_by = "open-gate"
    max_context_length = factory.Faker("random_int", min=64000, max=245600)
    costs = factory.LazyFunction(lambda: ModelCosts(prompt_tokens=0.0, completion_tokens=0.0))


class ModelsPayloadFactory(factory.DictFactory):
    class Meta:
        model = dict

    # object = "list"
    # data = factory.LazyFunction(lambda: [ModelPayloadFactory()])


class EmbeddingsPayloadFactory(factory.DictFactory):
    class Meta:
        model = dict

    object = "list"
    data = factory.LazyFunction(lambda: [{"embedding": [-0.30128387, 0.5073153, -0.807378], "index": 0, "object": "embedding"}])


@pytest.fixture
def gateway():
    return ModelProviderGateway()


@pytest.fixture
def model_http_client() -> ModelHttpClient:
    return ModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="test-model",
        model_hosting_zone=ProviderCarbonFootprintZone.WOR,
        model_total_params=10,
        model_active_params=10,
    )


class TestModelProviderGateway:
    @pytest.mark.parametrize(
        ("provider_type", "provider_class"),
        [
            (ProviderType.ALBERT, AlbertModelHttpClient),
            (ProviderType.MISTRAL, MistralModelHttpClient),
            (ProviderType.OPENAI, OpenaiModelHttpClient),
            (ProviderType.TEI, TeiModelHttpClient),
            (ProviderType.VLLM, VllmModelHttpClient),
        ],
    )
    def test_should_build_matching_http_client(self, provider_type, provider_class):
        # Arrange

        # Act
        result = ModelProviderGateway._build_client(provider_type, url="https://example.com", key="key", timeout=30, model_name="test-model")

        # Assert
        assert isinstance(result, provider_class)
        assert result.url == "https://example.com"
        assert result.key == "key"
        assert result.timeout == 30
        assert result.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_should_get_capabilities_for_generation_router(self, gateway, model_http_client, mocker):
        # Arrange
        mocked_build_client = mocker.patch.object(ModelProviderGateway, "_build_client", return_value=model_http_client)
        mocked_get_max_context_length = mocker.patch.object(ModelProviderGateway, "_get_max_context_length", AsyncMock(return_value=4096))
        mocked_get_vector_size = mocker.patch.object(ModelProviderGateway, "_get_vector_size", AsyncMock())

        # Act
        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.VLLM,
            url="https://example.com",
            key="key",
            timeout=30,
            model_name="test-model",
        )

        # Assert
        assert result == ProviderCapabilities(max_context_length=4096, vector_size=None)

    @pytest.mark.asyncio
    async def test_should_get_capabilities_for_embedding_router(self, gateway, model_http_client, mocker):
        # Arrange
        mocker.patch.object(ModelProviderGateway, "_build_client", return_value=model_http_client)
        mocker.patch.object(ModelProviderGateway, "_get_max_context_length", AsyncMock(return_value=2048))
        mocker.patch.object(ModelProviderGateway, "_get_vector_size", AsyncMock(return_value=3))

        # Act
        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url="https://example.com",
            key=None,
            timeout=30,
            model_name="test-model",
        )

        # Assert
        assert result == ProviderCapabilities(max_context_length=2048, vector_size=3)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [ProviderNotReachableError(model_name="test-model"), ModelProviderNotFoundError(model_name="test-model")])
    async def test_should_return_max_context_error(self, gateway, model_http_client, error, mocker):
        # Arrange
        mocker.patch.object(ModelProviderGateway, "_build_client", return_value=model_http_client)
        mocker.patch.object(ModelProviderGateway, "_get_max_context_length", AsyncMock(return_value=error))

        # Act
        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.VLLM,
            url="https://example.com",
            key=None,
            timeout=30,
            model_name="test-model",
        )

        # Assert
        assert result == error

    @pytest.mark.asyncio
    async def test_should_return_vector_size_error(self, gateway, model_http_client, mocker):
        # Arrange
        error = ProviderNotReachableError(model_name="test-model")
        mocker.patch.object(ModelProviderGateway, "_build_client", return_value=model_http_client)
        mocker.patch.object(ModelProviderGateway, "_get_max_context_length", AsyncMock(return_value=4096))
        mocker.patch.object(ModelProviderGateway, "_get_vector_size", AsyncMock(return_value=error))

        # Act
        result = await gateway.get_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url="https://example.com",
            key=None,
            timeout=30,
            model_name="test-model",
        )

        # Assert
        assert result == error

    @pytest.mark.asyncio
    async def test_should_get_max_context_length_from_model_id(self, model_http_client, mocker):
        # Arrange
        mock_exchange = ModelHttpExchange(
            original_request=OriginalModelRequest(endpoint=EndpointRoute.MODELS),
            formatted_request=FormattedModelRequest(method=HTTPMethod.GET, url="https://example.com/v1/models", body={}, form={}, files={}),
        )
        mocker.patch.object(model_http_client, "build_request_exchange", return_value=mock_exchange)
        mock_response = HttpResponseFactory(payload=MistralOriginalResponseFactory(models=True))
        mocker.patch.object(model_http_client, "forward_request", return_value=mock_response)

        # Act
        result = await ModelProviderGateway._get_max_context_length(model_http_client)

        # Assert
        assert result == 10
        model_http_client.build_request_exchange.assert_called_once()
        request = model_http_client.build_request_exchange.call_args.kwargs["user_request"]
        assert request.endpoint == EndpointRoute.MODELS
        model_http_client.forward_request.assert_awaited_once_with(exchange="exchange")

    @pytest.mark.asyncio
    async def test_should_get_max_context_length_from_alias(self, client):
        # Arrange
        client.model_name = "mistral-medium-latest"
        client.forward_request.return_value = HttpResponseFactory(
            payload=ModelsPayloadFactory(
                data=[ModelPayloadFactory(id="mistral-medium-2508", aliases=["mistral-medium-latest"], max_context_length=131072)]
            )
        )

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == 131072

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_missing_in_models_response(self, client):
        # Arrange
        client.forward_request.return_value = HttpResponseFactory(
            payload=ModelsPayloadFactory(data=[ModelPayloadFactory(id="other-model", aliases=["other-alias"])])
        )

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == ModelProviderNotFoundError(model_name="test-model")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [ModelIsTooBusyException(), HTTPException(status_code=500, detail="boom")])
    async def test_should_return_provider_not_reachable_when_getting_max_context_fails(self, client, error):
        # Arrange
        client.forward_request.side_effect = error

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")

    @pytest.mark.asyncio
    async def test_should_get_vector_size(self, client):
        # Arrange
        client.forward_request.return_value = HttpResponseFactory(payload=EmbeddingsPayloadFactory())

        # Act
        result = await ModelProviderGateway._get_vector_size(client)

        # Assert
        assert result == 3
        client.build_request_exchange.assert_called_once()
        request = client.build_request_exchange.call_args.kwargs["user_request"]
        assert request.endpoint == EndpointRoute.EMBEDDINGS
        assert request.body == {"model": "test-model", "input": "hello world"}
        client.forward_request.assert_awaited_once_with(exchange="exchange")

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_when_embeddings_status_is_not_200(self, client):
        # Arrange
        client.forward_request.return_value = HttpResponseFactory(status_code=500, payload=EmbeddingsPayloadFactory())

        # Act
        result = await ModelProviderGateway._get_vector_size(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [ModelIsTooBusyException(), HTTPException(status_code=500, detail="boom")])
    async def test_should_return_provider_not_reachable_when_getting_vector_size_fails(self, client, error):
        # Arrange
        client.forward_request.side_effect = error

        # Act
        result = await ModelProviderGateway._get_vector_size(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")
