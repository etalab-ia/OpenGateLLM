from api.domain.embeddings.entities import CreateEmbeddingsBody
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError
from api.domain.provider import ProviderAdapter, ProviderAdapterBuilder, ProviderClient
from api.domain.provider.entities import Provider, ProviderCapabilities, ProviderOriginalRequest, ProviderOriginalResponse, ProviderType
from api.domain.provider.errors import ProviderNotReachableError
from api.utils.variables import EndpointRoute


class ProviderCapabilitiesProbe:
    def __init__(self, provider_client: ProviderClient, provider_adapter_builder: ProviderAdapterBuilder):
        self.provider_client = provider_client
        self.provider_adapter_builder = provider_adapter_builder

    async def get_capabilities(
        self,
        router_type: RouterType,
        provider_type: ProviderType,
        url: str,
        key: str | None,
        timeout: int,
        model_name: str,
    ) -> ProviderCapabilities | ModelNotFoundError | ProviderNotReachableError:
        provider = Provider(
            id=0,
            user_id=0,
            router_id=0,
            type=provider_type,
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            created=0,
            updated=0,
        )
        adapter = self.provider_adapter_builder.build(endpoint=EndpointRoute.MODELS, provider=provider)

        result = await self._get_max_context_length(adapter=adapter)
        match result:
            case ProviderNotReachableError() as error:
                return error
            case ModelNotFoundError() as error:
                return error
            case _:
                max_context_length = result

        vector_size = None
        if router_type == RouterType.TEXT_EMBEDDINGS_INFERENCE:
            adapter = self.provider_adapter_builder.build(endpoint=EndpointRoute.EMBEDDINGS, provider=provider)
            result = await self._get_vector_size(adapter=adapter)
            match result:
                case ProviderNotReachableError() as error:
                    return error
                case _:
                    vector_size = result

        return ProviderCapabilities(max_context_length=max_context_length, vector_size=vector_size)

    async def _get_max_context_length(self, adapter: ProviderAdapter) -> int | None | ModelNotFoundError | ProviderNotReachableError:
        original_request = ProviderOriginalRequest(endpoint=EndpointRoute.MODELS)
        formatted_request = adapter.format_request(original_request=original_request)
        response = await self.provider_client.forward_request(provider=adapter.provider, formatted_request=formatted_request)
        match response:
            case ProviderOriginalResponse() as response:
                pass
            case error:
                return ProviderNotReachableError(model_name=adapter.provider.model_name, status_code=error.status_code, detail=error.detail)

        formatted_response = adapter.format_response(original_response=response, original_request=original_request)
        model_name = adapter.provider.model_name
        model = next((model for model in formatted_response.data.data if model.id == model_name or model_name in model.aliases), None)
        if model is None:
            return ModelNotFoundError(name=model_name)

        return model.max_context_length

    async def _get_vector_size(self, adapter: ProviderAdapter) -> int | ProviderNotReachableError:
        original_request = ProviderOriginalRequest(
            endpoint=EndpointRoute.EMBEDDINGS,
            body=CreateEmbeddingsBody(model=adapter.provider.model_name, input="hello world"),
        )
        formatted_request = adapter.format_request(original_request=original_request)
        response = await self.provider_client.forward_request(provider=adapter.provider, formatted_request=formatted_request)
        match response:
            case ProviderOriginalResponse() as response:
                pass
            case error:
                return ProviderNotReachableError(model_name=adapter.provider.model_name, status_code=error.status_code, detail=error.detail)

        formatted_response = adapter.format_response(original_response=response, original_request=original_request)
        vector_size = len(formatted_response.data.data[0].embedding)

        return vector_size
