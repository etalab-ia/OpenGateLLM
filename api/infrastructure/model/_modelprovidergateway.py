from api.domain.model import ModelType as RouterType
from api.domain.provider import ProviderCapabilities, ProviderGateway, ProviderNotReachableError
from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model import (
    AlbertModelHttpClient,
    MistralModelHttpClient,
    ModelHttpClient,
    OpenaiModelHttpClient,
    TeiModelHttpClient,
    VllmModelHttpClient,
)


class ModelProviderGateway(ProviderGateway):
    async def get_capabilities(self, router_type, provider_type, url, key, timeout, model_name) -> ProviderCapabilities | ProviderNotReachableError:
        client = ModelProviderGateway._build_client(provider_type, url, key, timeout, model_name)
        model_info = await client.get_model_info()

        if model_info is None:
            return ProviderNotReachableError(model_name)

        max_context_length = model_info.max_context_length

        if router_type == RouterType.TEXT_EMBEDDINGS_INFERENCE:
            vector_size = await client.get_vector_size()
        else:
            vector_size = None

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

        return provider_class[provider_type](
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_active_params=None,
            model_total_params=None,
            model_hosting_zone=None,
        )
