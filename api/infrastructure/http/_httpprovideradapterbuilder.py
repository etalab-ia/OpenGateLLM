from api.domain.provider import ProviderAdapterBuilder
from api.domain.provider.entities import Provider, ProviderType
from api.domain.provider.errors import UnsupportedProviderEndpointError
from api.infrastructure.http.adapters import HttpProviderAdapter
from api.infrastructure.http.adapters.audio.albert import AlbertAudioTranscriptionsAdapter
from api.infrastructure.http.adapters.audio.mistral import MistralAudioTranscriptionsAdapter
from api.infrastructure.http.adapters.audio.openai import OpenaiAudioTranscriptionsAdapter
from api.infrastructure.http.adapters.audio.vllm import VllmAudioTranscriptionsAdapter
from api.infrastructure.http.adapters.chat.albert import AlbertChatCompletionsAdapter
from api.infrastructure.http.adapters.chat.mistral import MistralChatCompletionsAdapter
from api.infrastructure.http.adapters.chat.openai import OpenaiChatCompletionsAdapter
from api.infrastructure.http.adapters.chat.vllm import VllmChatCompletionsAdapter
from api.infrastructure.http.adapters.embeddings.albert import AlbertEmbeddingsAdapter
from api.infrastructure.http.adapters.embeddings.mistral import MistralEmbeddingsAdapter
from api.infrastructure.http.adapters.embeddings.openai import OpenaiEmbeddingsAdapter
from api.infrastructure.http.adapters.embeddings.tei import TeiEmbeddingsAdapter
from api.infrastructure.http.adapters.embeddings.vllm import VllmEmbeddingsAdapter
from api.infrastructure.http.adapters.models.albert import AlbertModelsAdapter
from api.infrastructure.http.adapters.models.mistral import MistralModelsAdapter
from api.infrastructure.http.adapters.models.openai import OpenaiModelsAdapter
from api.infrastructure.http.adapters.models.tei import TeiModelsAdapter
from api.infrastructure.http.adapters.models.vllm import VllmModelsAdapter
from api.infrastructure.http.adapters.ocr.albert import AlbertOcrAdapter
from api.infrastructure.http.adapters.ocr.mistral import MistralOcrAdapter
from api.infrastructure.http.adapters.rerank.albert import AlbertRerankAdapter
from api.infrastructure.http.adapters.rerank.tei import TeiRerankAdapter
from api.infrastructure.http.adapters.rerank.vllm import VllmRerankAdapter
from api.utils.variables import EndpointRoute


class HttpProviderAdapterBuilder(ProviderAdapterBuilder):
    ADAPTER_REGISTRY = {
        EndpointRoute.AUDIO_TRANSCRIPTIONS: {
            ProviderType.ALBERT: AlbertAudioTranscriptionsAdapter,
            ProviderType.MISTRAL: MistralAudioTranscriptionsAdapter,
            ProviderType.OPENAI: OpenaiAudioTranscriptionsAdapter,
            ProviderType.VLLM: VllmAudioTranscriptionsAdapter,
        },
        EndpointRoute.CHAT_COMPLETIONS: {
            ProviderType.ALBERT: AlbertChatCompletionsAdapter,
            ProviderType.MISTRAL: MistralChatCompletionsAdapter,
            ProviderType.OPENAI: OpenaiChatCompletionsAdapter,
            ProviderType.VLLM: VllmChatCompletionsAdapter,
        },
        EndpointRoute.EMBEDDINGS: {
            ProviderType.ALBERT: AlbertEmbeddingsAdapter,
            ProviderType.MISTRAL: MistralEmbeddingsAdapter,
            ProviderType.OPENAI: OpenaiEmbeddingsAdapter,
            ProviderType.TEI: TeiEmbeddingsAdapter,
            ProviderType.VLLM: VllmEmbeddingsAdapter,
        },
        EndpointRoute.MODELS: {
            ProviderType.ALBERT: AlbertModelsAdapter,
            ProviderType.MISTRAL: MistralModelsAdapter,
            ProviderType.OPENAI: OpenaiModelsAdapter,
            ProviderType.TEI: TeiModelsAdapter,
            ProviderType.VLLM: VllmModelsAdapter,
        },
        EndpointRoute.OCR: {
            ProviderType.ALBERT: AlbertOcrAdapter,
            ProviderType.MISTRAL: MistralOcrAdapter,
        },
        EndpointRoute.RERANK: {
            ProviderType.ALBERT: AlbertRerankAdapter,
            ProviderType.TEI: TeiRerankAdapter,
            ProviderType.VLLM: VllmRerankAdapter,
        },
    }

    def build(self, endpoint: EndpointRoute, provider: Provider) -> HttpProviderAdapter | UnsupportedProviderEndpointError:
        adapter = self.ADAPTER_REGISTRY.get(endpoint, {}).get(provider.type)
        if adapter is None:
            return UnsupportedProviderEndpointError(endpoint=endpoint, provider_type=provider.type)

        return adapter(provider=provider)
