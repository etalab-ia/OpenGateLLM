from unittest.mock import AsyncMock, Mock

import pytest

from api.domain.model.entities import ModelType as RouterType
from api.domain.provider import ProviderCapabilities
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import ModelProviderNotFoundError, ProviderNotReachableError
from api.infrastructure.http.model import ModelHttpClient
from api.infrastructure.http.model.albert import AlbertModelHttpClient
from api.infrastructure.http.model.mistral import MistralModelHttpClient
from api.infrastructure.http.model.openai import OpenaiModelHttpClient
from api.infrastructure.http.model.tei import TeiModelHttpClient
from api.infrastructure.http.model.vllm import VllmModelHttpClient
from api.infrastructure.model._modelprovidergateway import ModelProviderGateway
from api.tests.integration.factories.albert import AlbertModelResponseFactory, AlbertModelsResponseFactory
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory
from api.tests.unit.infrastructure.http.model.factories import HttpResponseFactory
from api.utils.exceptions import HTTPException, ModelIsTooBusyException
from api.utils.variables import EndpointRoute


@pytest.fixture
def gateway() -> ModelProviderGateway:
    return ModelProviderGateway(metrics_logger=Mock(), request_manager=Mock())


@pytest.fixture
def client() -> ModelHttpClient:
    return ModelHttpClient(
        url="https://test.com",
        key="test-key",
        timeout=120,
        model_name="test-model",
        metrics_logger=Mock(),
        request_manager=Mock(),
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
        gateway = ModelProviderGateway(metrics_logger=Mock(), request_manager=Mock())
        # Act
        result = gateway._build_client(
            provider_type=provider_type,
            url="https://example.com",
            key="key",
            timeout=30,
            model_name="test-model",
        )

        # Assert
        assert isinstance(result, provider_class)
        assert result.url == "https://example.com"
        assert result.key == "key"
        assert result.timeout == 30
        assert result.model_name == "test-model"

    @pytest.mark.asyncio
    async def test_should_get_capabilities_for_generation_router(self, gateway, client, mocker):
        # Arrange
        mocked_build_client = mocker.patch.object(ModelProviderGateway, "_build_client", return_value=client)
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
        mocked_build_client.assert_called_once()
        mocked_get_max_context_length.assert_called_once()
        mocked_get_vector_size.assert_not_called()
        assert result == ProviderCapabilities(max_context_length=4096, vector_size=None)

    @pytest.mark.asyncio
    async def test_should_get_capabilities_for_embedding_router(self, gateway, client, mocker):
        # Arrange
        mocked_build_client = mocker.patch.object(ModelProviderGateway, "_build_client", return_value=client)
        mocked_get_max_context_length = mocker.patch.object(ModelProviderGateway, "_get_max_context_length", AsyncMock(return_value=2048))
        mocked_get_vector_size = mocker.patch.object(ModelProviderGateway, "_get_vector_size", AsyncMock(return_value=3))

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
        mocked_build_client.assert_called_once()
        mocked_get_max_context_length.assert_called_once()
        mocked_get_vector_size.assert_called_once()
        assert result == ProviderCapabilities(max_context_length=2048, vector_size=3)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [ProviderNotReachableError(model_name="test-model"), ModelProviderNotFoundError(model_name="test-model")])
    async def test_should_return_max_context_error(self, gateway, client, error, mocker):
        # Arrange
        mocker.patch.object(ModelProviderGateway, "_build_client", return_value=client)
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
    async def test_should_return_vector_size_error(self, gateway, client, mocker):
        # Arrange
        error = ProviderNotReachableError(model_name="test-model")
        mocker.patch.object(ModelProviderGateway, "_build_client", return_value=client)
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
    async def test_should_get_max_context_length_when_model_id_is_found(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mock_response = HttpResponseFactory(
            payload=AlbertModelsResponseFactory(
                count=2, data=[AlbertModelResponseFactory(id="test-model", aliases=["test-model-alias"], max_context_length=10)]
            )
        )
        mocker.patch.object(client, "forward_request", return_value=mock_response)

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == 10
        client.build_request_exchange.assert_called_once()
        request = client.build_request_exchange.call_args.kwargs["user_request"]
        assert request.endpoint == EndpointRoute.MODELS
        client.forward_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_get_max_context_length_when_model_alias_is_found(self, client, mocker):
        # Arrange
        client.model_name = "model-alias"
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mock_response = HttpResponseFactory(
            payload=AlbertModelsResponseFactory(
                data=[
                    AlbertModelResponseFactory(aliases=["model-alias", "model-alias-2"], max_context_length=10),
                    AlbertModelResponseFactory(aliases=["model-alias-3"]),
                ]
            )
        )
        mocker.patch.object(client, "forward_request", return_value=mock_response)

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == 10

    @pytest.mark.asyncio
    async def test_sould_return_the_first_model_max_context_length_when_several_models_with_the_same_name_are_found(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mock_response = HttpResponseFactory(
            payload=AlbertModelsResponseFactory(
                data=[
                    AlbertModelResponseFactory(id="test-model", max_context_length=10),
                    AlbertModelResponseFactory(id="test-model", max_context_length=20),
                ]
            )
        )
        mocker.patch.object(client, "forward_request", return_value=mock_response)

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == 10

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_models_response_is_empty(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mock_response = HttpResponseFactory(payload=AlbertModelsResponseFactory(data=[]))
        mocker.patch.object(client, "forward_request", return_value=mock_response)

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == ModelProviderNotFoundError(model_name="test-model")

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_model_is_missing_in_models_response(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mock_response = HttpResponseFactory(payload=AlbertModelsResponseFactory(data=[AlbertModelResponseFactory()]))
        mocker.patch.object(client, "forward_request", return_value=mock_response)

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == ModelProviderNotFoundError(model_name="test-model")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [ModelIsTooBusyException(), HTTPException(status_code=500, detail="boom")])
    async def test_should_return_provider_not_reachable_when_getting_max_context_fails(self, client, error, mocker):
        # Arrange
        mocker.patch.object(client, "forward_request", side_effect=error)

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_when_models_response_status_is_not_200(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mocker.patch.object(
            client, "forward_request", return_value=HttpResponseFactory(status_code=500, payload=AlbertModelsResponseFactory(data=[]))
        )

        # Act
        result = await ModelProviderGateway._get_max_context_length(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")

    @pytest.mark.asyncio
    async def test_should_get_vector_size(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mocker.patch.object(client, "forward_request", return_value=HttpResponseFactory(payload=TeiEmbeddingsResponseFactory(dimensions=3)))

        # Act
        result = await ModelProviderGateway._get_vector_size(client)

        # Assert
        assert result == 3
        client.build_request_exchange.assert_called_once()
        request = client.build_request_exchange.call_args.kwargs["user_request"]
        assert request.endpoint == EndpointRoute.EMBEDDINGS
        client.forward_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_when_embeddings_status_is_not_200(self, client, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mocker.patch.object(
            client, "forward_request", return_value=HttpResponseFactory(status_code=500, payload=TeiEmbeddingsResponseFactory(dimensions=3))
        )

        # Act
        result = await ModelProviderGateway._get_vector_size(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error", [ModelIsTooBusyException(), HTTPException(status_code=500, detail="boom")])
    async def test_should_return_provider_not_reachable_when_getting_vector_size_fails(self, client, error, mocker):
        # Arrange
        mocker.patch.object(client, "build_request_exchange", return_value=Mock())
        mocker.patch.object(client, "forward_request", side_effect=error)

        # Act
        result = await ModelProviderGateway._get_vector_size(client)

        # Assert
        assert result == ProviderNotReachableError(model_name="test-model")
