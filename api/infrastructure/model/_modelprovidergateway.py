import logging

from api.domain.model.entities import ModelType as RouterType
from api.domain.model.entities import UserModelRequest
from api.domain.provider import ProviderCapabilities, ProviderGateway, ProviderMetricsLogger
from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import ModelProviderNotFoundError, ProviderNotReachableError
from api.infrastructure.fastapi.context import RequestContextManager
from api.infrastructure.fastapi.schemas.models import ModelResponse
from api.infrastructure.http.model import ModelHttpClient, ModelUsageComputer
from api.infrastructure.http.model.albert import AlbertModelHttpClient
from api.infrastructure.http.model.mistral import MistralModelHttpClient
from api.infrastructure.http.model.openai import OpenaiModelHttpClient
from api.infrastructure.http.model.tei import TeiModelHttpClient
from api.infrastructure.http.model.vllm import VllmModelHttpClient
from api.utils.exceptions import HTTPException, ModelIsTooBusyException
from api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


class ModelProviderGateway(ProviderGateway):
    def __init__(self, provider_metrics_logger: ProviderMetricsLogger, request_manager: RequestContextManager):
        self.provider_metrics_logger = provider_metrics_logger
        self.request_manager = request_manager

    async def get_capabilities(
        self,
        router_type: RouterType,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
    ) -> ProviderCapabilities | ModelProviderNotFoundError | ProviderNotReachableError:
        client = self._build_client(provider_type=provider_type, url=url, key=key, timeout=timeout, model_name=model_name)

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

    def _build_client(
        self,
        provider_type,
        url,
        key,
        timeout,
        model_name,
        usage_computer: ModelUsageComputer | None = None,
    ) -> ModelHttpClient:
        provider_class: dict[ProviderType, type[ModelHttpClient]] = {
            ProviderType.ALBERT: AlbertModelHttpClient,
            ProviderType.MISTRAL: MistralModelHttpClient,
            ProviderType.OPENAI: OpenaiModelHttpClient,
            ProviderType.TEI: TeiModelHttpClient,
            ProviderType.VLLM: VllmModelHttpClient,
        }

        return provider_class[provider_type](
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            provider_metrics_logger=self.provider_metrics_logger,
            request_manager=self.request_manager,
            usage_computer=usage_computer,
        )

    @staticmethod
    async def _get_max_context_length(client: ModelHttpClient) -> int | None | ProviderNotReachableError | ModelProviderNotFoundError:
        request = UserModelRequest(endpoint=EndpointRoute.MODELS)
        try:
            exchange = client.build_request_exchange(user_request=request)
            response = await client.forward_request(exchange=exchange)
        # @TODO: handle exception properly and add integration tests for this case and adapt unit tests
        except (ModelIsTooBusyException, HTTPException) as e:
            logger.info(msg=f"Failed to get max context length for {client.model_name}: {e}.")
            return ProviderNotReachableError(model_name=client.model_name, status_code=500, detail=str(e))

        if response.status_code != 200:
            return ProviderNotReachableError(model_name=client.model_name, status_code=response.status_code, detail=response.text)

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
            return ProviderNotReachableError(model_name=client.model_name, status_code=500, detail=str(e))

        if response.status_code != 200:
            return ProviderNotReachableError(model_name=client.model_name, status_code=response.status_code, detail=response.text)

        data = response.json()["data"]
        vector_size = len(data[0]["embedding"])

        return vector_size
