from api.domain.embeddings.entities import CreateEmbeddingsBody
from api.domain.model.entities import ModelType as RouterType
from api.domain.model.errors import ModelNotFoundError
from api.domain.provider import ProviderAdapter, ProviderAdapterBuilder, ProviderClient
from api.domain.provider.entities import Provider, ProviderCapabilities, ProviderRawResponse, ProviderRequest, ProviderType
from api.domain.provider.errors import ProviderInvalidResponseError, ProviderNotReachableError
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
    ) -> ProviderCapabilities | ModelNotFoundError | ProviderNotReachableError | ProviderInvalidResponseError:
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
                case ProviderInvalidResponseError() as error:
                    return error
                case _:
                    vector_size = result

        return ProviderCapabilities(max_context_length=max_context_length, vector_size=vector_size)

    async def _get_max_context_length(self, adapter: ProviderAdapter) -> int | None | ModelNotFoundError | ProviderNotReachableError:
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)
        response = await self.provider_client.forward(provider=adapter.provider, request=request)
        match response:
            case ProviderRawResponse() as response:
                pass
            case error:
                return ProviderNotReachableError(model_name=adapter.provider.model_name, status_code=error.status_code, detail=error.detail)

        provider_response = adapter.to_domain_response(raw_response=response, request=request)
        model_name = adapter.provider.model_name
        model = next((m for m in provider_response.data.data if m.id == model_name or model_name in m.aliases), None)
        if model is None:
            return ModelNotFoundError(name=model_name)

        return model.max_context_length

    async def _get_vector_size(self, adapter: ProviderAdapter) -> int | ProviderNotReachableError | ProviderInvalidResponseError:
        request = ProviderRequest(
            endpoint=EndpointRoute.EMBEDDINGS,
            payload=CreateEmbeddingsBody(model=adapter.provider.model_name, input="hello world"),
        )
        response = await self.provider_client.forward(provider=adapter.provider, request=request)
        match response:
            case ProviderRawResponse() as response:
                pass
            case error:
                return ProviderNotReachableError(model_name=adapter.provider.model_name, status_code=error.status_code, detail=error.detail)

        provider_response = adapter.to_domain_response(raw_response=response, request=request)
        if not provider_response.data.data:
            return ProviderInvalidResponseError(model_name=adapter.provider.model_name, detail="no embedding returned")

        vector_size = len(provider_response.data.data[0].embedding)

        return vector_size
