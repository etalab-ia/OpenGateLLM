from unittest.mock import create_autospec

from openai.types import Embedding
import pytest

from api.domain.embeddings.entities import Embeddings
from api.domain.model.entities import Model, Models
from api.domain.model.errors import ModelNotFoundError, StatusCodeModelError
from api.domain.provider import ProviderClient
from api.domain.provider.entities import ProviderCapabilities, ProviderResponse, ProviderType
from api.domain.provider.errors import (
    ProviderAdapterValidationResponseError,
    ProviderInvalidResponseError,
    ProviderNotReachableError,
    UnsupportedProviderEndpointError,
)
from api.domain.router.entities import RouterType
from api.use_cases.services import ProviderCapabilitiesProbe
from api.utils.variables import EndpointRoute

DEFAULT_PROVIDER_URL = "https://test.com"
DEFAULT_PROVIDER_KEY = "test-key"
DEFAULT_PROVIDER_TIMEOUT = 30
DEFAULT_MODEL_ID = "test-model"


@pytest.fixture
def provider_client():
    return create_autospec(ProviderClient, instance=True, spec_set=True)


@pytest.fixture
def probe(provider_client) -> ProviderCapabilitiesProbe:
    return ProviderCapabilitiesProbe(provider_client=provider_client)


def model_entity(model_id: str = DEFAULT_MODEL_ID, aliases: list[str] | None = None, max_context_length: int | None = 4096) -> Model:
    return Model(
        id=model_id,
        aliases=aliases or [],
        created=0,
        owned_by="test",
        max_context_length=max_context_length,
        type=RouterType.TEXT_GENERATION,
    )


def models_formatted_response(*models: Model) -> ProviderResponse:
    return ProviderResponse(id="req-123", data=Models(data=list(models)))


def embeddings_formatted_response(dimensions: int = 3) -> ProviderResponse:
    return ProviderResponse(
        id="req-123",
        data=Embeddings(
            id="embeddings-1",
            model=DEFAULT_MODEL_ID,
            data=[Embedding(embedding=[0.1] * dimensions, index=0, object="embedding")],
        ),
    )


def empty_embeddings_formatted_response() -> ProviderResponse:
    return ProviderResponse(id="req-123", data=Embeddings(id="embeddings-1", model=DEFAULT_MODEL_ID, data=[]))


class TestProviderCapabilitiesProbe:
    @pytest.mark.asyncio
    async def test_should_get_capabilities_from_the_models_endpoint_only_for_a_generation_router(self, probe, provider_client):
        provider_client.forward.return_value = models_formatted_response(model_entity(max_context_length=4096))

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=DEFAULT_PROVIDER_KEY,
            timeout=DEFAULT_PROVIDER_TIMEOUT,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=4096, vector_size=None)
        provider_client.forward.assert_awaited_once()
        assert provider_client.forward.await_args.kwargs["request"].endpoint == EndpointRoute.MODELS
        probed_provider = provider_client.forward.await_args.kwargs["provider"]
        assert probed_provider.type == ProviderType.ALBERT
        assert probed_provider.model_name == DEFAULT_MODEL_ID
        assert probed_provider.url == DEFAULT_PROVIDER_URL
        assert probed_provider.key == DEFAULT_PROVIDER_KEY
        assert probed_provider.timeout == DEFAULT_PROVIDER_TIMEOUT

    @pytest.mark.asyncio
    async def test_should_get_capabilities_from_the_models_and_embeddings_endpoints_for_an_embeddings_router(self, probe, provider_client):
        provider_client.forward.side_effect = [
            models_formatted_response(model_entity(max_context_length=2048)),
            embeddings_formatted_response(dimensions=3),
        ]

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=2048, vector_size=3)
        assert [call.kwargs["request"].endpoint for call in provider_client.forward.await_args_list] == [
            EndpointRoute.MODELS,
            EndpointRoute.EMBEDDINGS,
        ]
        assert provider_client.forward.await_args.kwargs["provider"].type == ProviderType.TEI
        embeddings_request = provider_client.forward.await_args_list[1].kwargs["request"]
        assert embeddings_request.payload.model == DEFAULT_MODEL_ID

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_error_when_models_request_fails(self, probe, provider_client):
        provider_client.forward.return_value = StatusCodeModelError(status_code=500, detail="error_detail")

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderNotReachableError(model_name=DEFAULT_MODEL_ID, status_code=500, detail="error_detail")

    @pytest.mark.asyncio
    async def test_should_return_provider_invalid_response_error_when_the_provider_type_has_no_adapter(self, probe, provider_client):
        provider_client.forward.return_value = UnsupportedProviderEndpointError(endpoint=EndpointRoute.MODELS, provider_type=ProviderType.ALBERT)

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderInvalidResponseError(model_name=DEFAULT_MODEL_ID, detail="provider type does not expose /models")

    @pytest.mark.asyncio
    async def test_should_return_provider_invalid_response_error_when_the_models_payload_does_not_parse(self, probe, provider_client):
        provider_client.forward.return_value = ProviderAdapterValidationResponseError(provider_type=ProviderType.ALBERT, errors=[{"msg": "invalid"}])

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderInvalidResponseError(model_name=DEFAULT_MODEL_ID, detail="[{'msg': 'invalid'}]")

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_error_when_model_is_absent_from_models_response(self, probe, provider_client):
        provider_client.forward.return_value = models_formatted_response(model_entity(model_id="another-model"))

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ModelNotFoundError(name=DEFAULT_MODEL_ID)

    @pytest.mark.asyncio
    async def test_should_return_provider_not_reachable_error_when_embeddings_request_fails(self, probe, provider_client):
        provider_client.forward.side_effect = [
            models_formatted_response(model_entity()),
            StatusCodeModelError(status_code=500, detail="error_detail"),
        ]

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderNotReachableError(model_name=DEFAULT_MODEL_ID, status_code=500, detail="error_detail")

    @pytest.mark.asyncio
    async def test_should_return_provider_invalid_response_error_when_embeddings_response_has_no_embedding(self, probe, provider_client):
        provider_client.forward.side_effect = [
            models_formatted_response(model_entity()),
            empty_embeddings_formatted_response(),
        ]

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_EMBEDDINGS_INFERENCE,
            provider_type=ProviderType.TEI,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=DEFAULT_PROVIDER_TIMEOUT,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderInvalidResponseError(model_name=DEFAULT_MODEL_ID, detail="no embedding returned")

    @pytest.mark.asyncio
    async def test_should_get_max_context_length_of_the_model_matching_the_requested_alias(self, probe, provider_client):
        provider_client.forward.return_value = models_formatted_response(
            model_entity(model_id="model-id", aliases=["model-alias", "model-alias-2"], max_context_length=10),
            model_entity(model_id="other-model", aliases=["model-alias-3"], max_context_length=20),
        )

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name="model-alias",
        )

        assert result == ProviderCapabilities(max_context_length=10, vector_size=None)

    @pytest.mark.asyncio
    async def test_should_return_the_first_model_max_context_length_when_several_models_with_the_same_name_are_found(self, probe, provider_client):
        provider_client.forward.return_value = models_formatted_response(model_entity(max_context_length=10), model_entity(max_context_length=20))

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=10, vector_size=None)

    @pytest.mark.asyncio
    async def test_should_return_capabilities_without_max_context_length_when_the_model_does_not_announce_one(self, probe, provider_client):
        provider_client.forward.return_value = models_formatted_response(model_entity(max_context_length=None))

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=DEFAULT_PROVIDER_TIMEOUT,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ProviderCapabilities(max_context_length=None, vector_size=None)

    @pytest.mark.asyncio
    async def test_should_return_model_not_found_error_when_models_response_is_empty(self, probe, provider_client):
        provider_client.forward.return_value = models_formatted_response()

        result = await probe.get_capabilities(
            router_type=RouterType.TEXT_GENERATION,
            provider_type=ProviderType.ALBERT,
            url=DEFAULT_PROVIDER_URL,
            key=None,
            timeout=30,
            model_name=DEFAULT_MODEL_ID,
        )

        assert result == ModelNotFoundError(name=DEFAULT_MODEL_ID)
