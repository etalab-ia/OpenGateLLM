import logging

from api.domain.model import ModelType as RouterType
from api.domain.model.entities import UserModelRequest
from api.domain.provider import ProviderCapabilities, ProviderGateway
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import ModelProviderNotFoundError, ProviderNotReachableError
from api.infrastructure.fastapi.schemas.models import ModelResponse
from api.infrastructure.http.model import (
    AlbertModelHttpClient,
    MistralModelHttpClient,
    ModelHttpClient,
    OpenaiModelHttpClient,
    TeiModelHttpClient,
    VllmModelHttpClient,
)
from api.utils.exceptions import HTTPException, ModelIsTooBusyException
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


class ModelProviderGateway(ProviderGateway):
    async def get_capabilities(
        self,
        router_type,
        provider_type,
        url,
        key,
        timeout,
        model_name,
    ) -> ProviderCapabilities | ModelProviderNotFoundError | ProviderNotReachableError:
        client = ModelProviderGateway._build_client(provider_type, url, key, timeout, model_name)

        result = await self._get_max_context_length(client=client)
        match result:
            case ProviderNotReachableError() as error:
                return error
            case ModelProviderNotFoundError() as error:
                return error
            case _:
                max_context_length = result

        # vector size
        vector_size = None
        if router_type == RouterType.TEXT_EMBEDDINGS_INFERENCE:
            result = await self._get_vector_size(client=client)
            match result:
                case ProviderNotReachableError() as error:
                    return error
                case _:
                    vector_size = result

        return ProviderCapabilities(max_context_length=max_context_length, vector_size=vector_size)

    @staticmethod
    def _build_client(provider_type, url, key, timeout, model_name) -> ModelHttpClient:
        provider_class: dict[ProviderType, type[ModelHttpClient]] = {
            ProviderType.ALBERT: AlbertModelHttpClient,
            ProviderType.MISTRAL: MistralModelHttpClient,
            ProviderType.OPENAI: OpenaiModelHttpClient,
            ProviderType.TEI: TeiModelHttpClient,
            ProviderType.VLLM: VllmModelHttpClient,
        }

        # @TODO: add model_hosting_zone, model_total_params, model_active_params
        return provider_class[provider_type](
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_active_params=None,
            model_total_params=None,
            model_hosting_zone=None,
        )

    @staticmethod
    async def _get_max_context_length(client: ModelHttpClient) -> int | None | ProviderNotReachableError | ModelProviderNotFoundError:
        request = UserModelRequest(endpoint=EndpointRoute.MODELS)
        try:
            exchange = client.build_request_exchange(user_request=request)
            response = await client.forward_request(exchange=exchange)
        except (ModelIsTooBusyException, HTTPException) as e:
            logger.info(msg=f"Failed to get max context length for {client.model_name}: {e}.")
            return ProviderNotReachableError(model_name=client.model_name)

        if response.status_code != 200:
            return ProviderNotReachableError(model_name=client.model_name)

        data = response.json().get("data", [])
        model = next((ModelResponse(**model) for model in data if model["id"] == client.model_name or client.model_name in model["aliases"]), None)
        if model is None:
            logger.info(msg=f"Model not found in response of {client.model_name}: {data}.")
            return ModelProviderNotFoundError(model_name=client.model_name)

        return model.max_context_length

    @staticmethod
    async def _get_vector_size(client: ModelHttpClient) -> int | ProviderNotReachableError:
        request = UserModelRequest(endpoint=EndpointRoute.EMBEDDINGS, body={"model": client.model_name, "input": "hello world"})
        try:
            exchange = client.build_request_exchange(user_request=request)
            response = await client.forward_request(exchange=exchange)
        except (ModelIsTooBusyException, HTTPException) as e:
            logger.info(msg=f"Failed to get vector size for {client.model_name}: {e}.")
            return ProviderNotReachableError(model_name=client.model_name)

        if response.status_code != 200:
            return ProviderNotReachableError(model_name=client.model_name)

        data = response.json()["data"]
        vector_size = len(data[0]["embedding"])

        return vector_size
