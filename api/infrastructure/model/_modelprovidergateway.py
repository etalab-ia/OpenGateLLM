from api.clients.model import BaseModelProvider
from api.domain.model import ModelType as RouterType
from api.domain.provider import ProviderCapabilities, ProviderGateway, ProviderNotReachableError


class ModelProviderGateway(ProviderGateway):
    async def get_capabilities(self, router_type, provider_type, url, key, timeout, model_name):
        try:
            client = self._build_client(provider_type, url, key, timeout, model_name)
            max_context_length = await client.get_max_context_length()
            if router_type == RouterType.TEXT_EMBEDDINGS_INFERENCE:
                vector_size = await client.get_vector_size()
            else:
                vector_size = None
            return ProviderCapabilities(
                max_context_length=max_context_length,
                vector_size=vector_size,
            )
        except AssertionError as e:
            return ProviderNotReachableError(model_name)

    def _build_client(self, provider_type, url, key, timeout, model_name):
        cls = BaseModelProvider.import_module(type=provider_type)
        return cls(
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_hosting_zone=None,
            model_total_params=0,
            model_active_params=0,
        )
