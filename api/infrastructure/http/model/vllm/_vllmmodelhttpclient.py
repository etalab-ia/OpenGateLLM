from http import HTTPMethod

from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model import ModelHttpClient, ModelHttpClientEndpoints
from api.utils.variables import EndpointRoute

from .adapters import VllmModelsAdapter


class VllmModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(rerank=(HTTPMethod.POST, "/v2/rerank"))
    TYPE = ProviderType.VLLM

    def _build_adapters(self):
        adapters = super()._build_adapters()
        adapters[EndpointRoute.MODELS] = VllmModelsAdapter()
        return adapters
