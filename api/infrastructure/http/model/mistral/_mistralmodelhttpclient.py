from http import HTTPMethod

from api.domain.provider.entities import ProviderType
from api.infrastructure.http.model import ModelHttpClient, ModelHttpClientEndpoints
from api.utils.variables import EndpointRoute

from .adapters import MistralAudioTranscriptionAdapter, MistralChatCompletionAdapter, MistralModelsAdapter


class MistralModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(audio_transcriptions=(HTTPMethod.POST, "/v1/chat/completions"), rerank=(None, None))
    TYPE = ProviderType.MISTRAL

    def _build_adapters(self):
        adapters = super()._build_adapters()
        adapters[EndpointRoute.AUDIO_TRANSCRIPTIONS] = MistralAudioTranscriptionAdapter()
        adapters[EndpointRoute.CHAT_COMPLETIONS] = MistralChatCompletionAdapter()
        adapters[EndpointRoute.MODELS] = MistralModelsAdapter()
        return adapters
