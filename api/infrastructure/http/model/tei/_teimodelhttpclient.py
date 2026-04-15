from http import HTTPMethod

from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model import ModelHttpClient, ModelHttpClientEndpoints
from api.utils.variables import EndpointRoute

from .adapters import TeiModelsAdapter, TeiRerankAdapter


class TeiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(
        audio_transcriptions=(None, None),
        chat_completions=(None, None),
        models=(HTTPMethod.GET, "/info"),
        ocr=(None, None),
        rerank=(HTTPMethod.POST, "/rerank"),
    )
    TYPE = ProviderType.TEI

    def _build_adapters(self):
        adapters = super()._build_adapters()
        adapters[EndpointRoute.MODELS] = TeiModelsAdapter()
        adapters[EndpointRoute.RERANK] = TeiRerankAdapter()
        return adapters
