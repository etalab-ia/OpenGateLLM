from http import HTTPMethod
from unittest.mock import AsyncMock, Mock

import pytest

from api.domain.model.entities import Model, Models
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError, StatusCodeModelError
from api.domain.provider import ProviderCapabilitiesRepository
from api.domain.provider.entities import ProviderCapabilities, ProviderFormattedResponse, ProviderOriginalResponse, ProviderType
from api.domain.provider.errors import ProviderNotReachableError
from api.infrastructure.http import HttpProviderAdapterBuilder
from api.infrastructure.http.adapters.embeddings import EmbeddingsAdapter
from api.infrastructure.http.adapters.embeddings.tei import TeiEmbeddingsAdapter
from api.infrastructure.http.adapters.models import ModelsAdapter
from api.infrastructure.http.adapters.models.albert import AlbertModelsAdapter
from api.tests.integration.factories.albert import AlbertModelResponseFactory, AlbertModelsResponseFactory
from api.tests.integration.factories.tei import TeiEmbeddingsResponseFactory
from api.tests.unit.use_case.factories import ProviderFactory

DEFAULT_PROVIDER_URL = "https://test.com"
DEFAULT_MODEL_ID = "test-model"


@pytest.fixture
def provider_client() -> Mock:
    client = Mock()
    client.forward_request = AsyncMock()
    return client


@pytest.fixture
def provider_adapter_builder() -> HttpProviderAdapterBuilder:
    return HttpProviderAdapterBuilder()


@pytest.fixture
def repository(provider_client: Mock, provider_adapter_builder: HttpProviderAdapterBuilder) -> ProviderCapabilitiesRepository:
    return ProviderCapabilitiesRepository(provider_client=provider_client, provider_adapter_builder=provider_adapter_builder)


def provider_factory(provider_type: ProviderType = ProviderType.ALBERT, model_name: str = DEFAULT_MODEL_ID):
    return ProviderFactory(type=provider_type, url=DEFAULT_PROVIDER_URL, key="test-key", timeout=30, model_name=model_name)


def models_adapter(model_name: str = DEFAULT_MODEL_ID) -> AlbertModelsAdapter:
    return AlbertModelsAdapter(provider=provider_factory(model_name=model_name))


def embeddings_adapter() -> TeiEmbeddingsAdapter:
    return TeiEmbeddingsAdapter(provider=provider_factory(provider_type=ProviderType.TEI))


class TestProviderCapabilitiesRepository:
    @pytest.mark.asyncio
    async def test_should_get_capabilities_for_generation_router(self, repository: ProviderCapabilitiesRepository, mocker):
        mocked_get_max_context_length = mocker.patch.object(ProviderCapabilitiesRepository, "_get_max_context_length", AsyncMock(return_value=4096))
        mocked_get_vector_size = mocker.patch.object(ProviderCapabilitiesRepository, "_get_vector_size", AsyncMock())

        result = await repository.get_provider_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key="key",
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=4096, vector_size=None)
        mocked_get_max_context_length.assert_awaited_once()
        models_arg = mocked_get_max_context_length.call_args.kwargs["adapter"]
        assert isinstance(models_arg, ModelsAdapter)
        assert models_arg.provider.type == ProviderType.ALBERT
        assert models_arg.provider.model_name == DEFAULT_MODEL_ID
        mocked_get_vector_size.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_get_capabilities_for_embedding_router(self, repository: ProviderCapabilitiesRepository, mocker):
        mocked_get_max_context_length = mocker.patch.object(ProviderCapabilitiesRepository, "_get_max_context_length", AsyncMock(return_value=2048))
        mocked_get_vector_size = mocker.patch.object(ProviderCapabilitiesRepository, "_get_vector_size", AsyncMock(return_value=3))

        result = await repository.get_provider_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=2048, vector_size=3)
        mocked_get_max_context_length.assert_awaited_once()
        mocked_get_vector_size.assert_awaited_once()
        embeddings_arg = mocked_get_vector_size.call_args.kwargs["adapter"]
        assert isinstance(embeddings_arg, EmbeddingsAdapter)
        assert embeddings_arg.provider.type == ProviderType.TEI

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [ProviderNotReachableError(model_name=DEFAULT_MODEL_ID, status_code=500, detail="error_detail"), ModelNotFoundError(name=DEFAULT_MODEL_ID)],
    )
    async def test_should_return_max_context_error(self, repository: ProviderCapabilitiesRepository, error, mocker):
        mocker.patch.object(ProviderCapabilitiesRepository, "_get_max_context_length", AsyncMock(return_value=error))

        result = await repository.get_provider_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == error

    @pytest.mark.asyncio
    async def test_should_return_vector_size_error(self, repository: ProviderCapabilitiesRepository, mocker):
        error = ProviderNotReachableError(model_name=DEFAULT_MODEL_ID, status_code=500, detail="error_detail")
        mocker.patch.object(ProviderCapabilitiesRepository, "_get_max_context_length", AsyncMock(return_value=4096))
        mocker.patch.object(ProviderCapabilitiesRepository, "_get_vector_size", AsyncMock(return_value=error))

        result = await repository.get_provider_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == error

    @pytest.mark.asyncio
    async def test_should_get_max_context_length_when_model_id_is_found(self, repository: ProviderCapabilitiesRepository, provider_client: Mock):
        body = AlbertModelsResponseFactory(
            count=2,
            data=[AlbertModelResponseFactory(model=DEFAULT_MODEL_ID, aliases=["test-model-alias"], max_context_length=10)],
        )
        provider_client.forward_request.return_value = ProviderOriginalResponse(data=body)

        result = await repository._get_max_context_length(adapter=models_adapter())

        assert result == 10
        provider_client.forward_request.assert_awaited_once()
        formatted_request = provider_client.forward_request.call_args.kwargs["formatted_request"]
        assert formatted_request.method == HTTPMethod.GET
        assert formatted_request.url == f"{DEFAULT_PROVIDER_URL}/v1/models"

    @pytest.mark.asyncio
    async def test_should_get_max_context_length_when_model_alias_is_found(self, repository: ProviderCapabilitiesRepository, provider_client: Mock):
        adapter = Mock()
        adapter.provider = provider_factory(model_name="model-alias")
        adapter.format_request.return_value = Mock()
        adapter.format_response.return_value = ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id="model-id",
                        aliases=["model-alias", "model-alias-2"],
                        created=0,
                        owned_by="test",
                        max_context_length=10,
                        type=RouterType.TEXT_GENERATION,
                    ),
                    Model(
                        id="other-model",
                        aliases=["model-alias-3"],
                        created=0,
                        owned_by="test",
                        max_context_length=20,
                        type=RouterType.TEXT_GENERATION,
                    ),
                ]
            )
        )
        provider_client.forward_request.return_value = ProviderOriginalResponse(data={})

        result = await repository._get_max_context_length(adapter=adapter)

        assert result == 10

    @pytest.mark.asyncio
    async def test_should_return_the_first_model_max_context_length_when_several_models_with_the_same_name_are_found(
        self, repository: ProviderCapabilitiesRepository, provider_client: Mock
    ):
        body = AlbertModelsResponseFactory(
            data=[
                AlbertModelResponseFactory(model=DEFAULT_MODEL_ID, max_context_length=10),
                AlbertModelResponseFactory(model=DEFAULT_MODEL_ID, max_context_length=20),
            ]
        )
        provider_client.forward_request.return_value = ProviderOriginalResponse(data=body)

        result = await repository._get_max_context_length(adapter=models_adapter())

        assert result == 10

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_models_response_is_empty(
        self, repository: ProviderCapabilitiesRepository, provider_client: Mock
    ):
        provider_client.forward_request.return_value = ProviderOriginalResponse(data=AlbertModelsResponseFactory(data=[]))

        result = await repository._get_max_context_length(adapter=models_adapter())

        assert result == ModelNotFoundError(name=DEFAULT_MODEL_ID)

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_when_model_is_missing_in_models_response(
        self, repository: ProviderCapabilitiesRepository, provider_client: Mock
    ):
        provider_client.forward_request.return_value = ProviderOriginalResponse(data=AlbertModelsResponseFactory(data=[AlbertModelResponseFactory()]))

        result = await repository._get_max_context_length(adapter=models_adapter())

        assert result == ModelNotFoundError(name=DEFAULT_MODEL_ID)

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_when_getting_max_context_fails(
        self, repository: ProviderCapabilitiesRepository, provider_client: Mock
    ):
        provider_client.forward_request.return_value = StatusCodeModelError(status_code=500, detail="boom")

        result = await repository._get_max_context_length(adapter=models_adapter())

        assert result == ProviderNotReachableError(model_name=DEFAULT_MODEL_ID, status_code=500, detail="boom")

    @pytest.mark.asyncio
    async def test_should_get_vector_size(self, repository: ProviderCapabilitiesRepository, provider_client: Mock):
        provider_client.forward_request.return_value = ProviderOriginalResponse(
            data=TeiEmbeddingsResponseFactory(dimensions=3, model_id=DEFAULT_MODEL_ID)
        )

        result = await repository._get_vector_size(adapter=embeddings_adapter())

        assert result == 3
        provider_client.forward_request.assert_awaited_once()
        formatted_request = provider_client.forward_request.call_args.kwargs["formatted_request"]
        assert formatted_request.method == HTTPMethod.POST
        assert formatted_request.url == f"{DEFAULT_PROVIDER_URL}/v1/embeddings"
        assert formatted_request.body["model"] == DEFAULT_MODEL_ID

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_when_getting_vector_size_fails(
        self, repository: ProviderCapabilitiesRepository, provider_client: Mock
    ):
        provider_client.forward_request.return_value = StatusCodeModelError(status_code=500, detail="boom")

        result = await repository._get_vector_size(adapter=embeddings_adapter())

        assert result == ProviderNotReachableError(model_name=DEFAULT_MODEL_ID, status_code=500, detail="boom")
