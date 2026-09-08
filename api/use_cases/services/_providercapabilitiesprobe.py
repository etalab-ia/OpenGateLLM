from typing import assert_never

from api.domain.embeddings.entities import CreateEmbeddingsBody
from api.domain.model.errors import ModelNotFoundError, StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider import ProviderClient, ProviderClientError
from api.domain.provider.entities import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse, ProviderType
from api.domain.provider.errors import (
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    ProviderInvalidResponseError,
    ProviderNotReachableError,
    UnsupportedProviderEndpointError,
)
from api.domain.router.entities import RouterType
from api.utils.variables import EndpointRoute


class ProviderCapabilitiesProbe:
    def __init__(self, provider_client: ProviderClient):
        self.provider_client = provider_client

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
        result = await self._get_max_context_length(provider=provider)
        match result:
            case ProviderNotReachableError() as error:
                return error
            case ProviderInvalidResponseError() as error:
                return error
            case ModelNotFoundError() as error:
                return error
            case int() | None:
                max_context_length = result
            case _ as unreachable:
                assert_never(unreachable)

        vector_size = None
        if router_type == RouterType.TEXT_EMBEDDINGS_INFERENCE:
            result = await self._get_vector_size(provider=provider)
            match result:
                case ProviderNotReachableError() as error:
                    return error
                case ProviderInvalidResponseError() as error:
                    return error
                case int():
                    vector_size = result
                case _ as unreachable:
                    assert_never(unreachable)

        return ProviderCapabilities(max_context_length=max_context_length, vector_size=vector_size)

    async def _get_max_context_length(
        self,
        provider: Provider,
    ) -> int | None | ModelNotFoundError | ProviderNotReachableError | ProviderInvalidResponseError:
        request = ProviderRequest(endpoint=EndpointRoute.MODELS)
        response = await self.provider_client.forward(provider=provider, request=request)
        match response:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return self._to_probe_error(provider=provider, error=error)

        model_name = provider.model_name
        model = next((m for m in provider_response.data.data if m.id == model_name or model_name in m.aliases), None)
        if model is None:
            return ModelNotFoundError(name=model_name)

        return model.max_context_length

    async def _get_vector_size(self, provider: Provider) -> int | ProviderNotReachableError | ProviderInvalidResponseError:
        request = ProviderRequest(
            endpoint=EndpointRoute.EMBEDDINGS,
            payload=CreateEmbeddingsBody(model=provider.model_name, input="hello world"),
        )
        response = await self.provider_client.forward(provider=provider, request=request)
        match response:
            case ProviderResponse() as provider_response:
                pass
            case error:
                return self._to_probe_error(provider=provider, error=error)

        if not provider_response.data.data:
            return ProviderInvalidResponseError(model_name=provider.model_name, detail="no embedding returned")

        vector_size = len(provider_response.data.data[0].embedding)

        return vector_size

    @staticmethod
    def _to_probe_error(provider: Provider, error: ProviderClientError) -> ProviderNotReachableError | ProviderInvalidResponseError:
        match error:
            case StatusCodeModelError() | TooBusyModelError() | UnknownModelError():
                return ProviderNotReachableError(model_name=provider.model_name, status_code=error.status_code, detail=error.detail)
            case UnsupportedProviderEndpointError(endpoint=endpoint):
                return ProviderInvalidResponseError(model_name=provider.model_name, detail=f"provider type does not expose {endpoint}")
            case ProviderAdapterValidationRequestError(errors=errors) | ProviderAdapterValidationResponseError(errors=errors):
                return ProviderInvalidResponseError(model_name=provider.model_name, detail=str(errors))
            case _ as unreachable:
                assert_never(unreachable)
