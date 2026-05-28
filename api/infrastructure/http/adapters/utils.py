from pydantic import BaseModel, ConfigDict

from api.domain.model import ModelEnvironmentalImpactsComputer, ModelTokenizer
from api.domain.provider.entities import Provider, ProviderType
from api.domain.provider.errors import UnsupportedProviderEndpointError
from api.infrastructure.http.adapters import (
    AudioTranscriptionsAdapter,
    ChatCompletionsAdapter,
    EmbeddingsAdapter,
    EndpointAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)
from api.infrastructure.http.adapters.albert import (
    AlbertAudioTranscriptionAdapter,
    AlbertChatCompletionAdapter,
    AlbertEmbeddingsAdapter,
    AlbertModelsAdapter,
    AlbertOcrAdapter,
    AlbertRerankAdapter,
)
from api.infrastructure.http.adapters.mistral import (
    MistralAudioTranscriptionAdapter,
    MistralChatCompletionAdapter,
    MistralEmbeddingsAdapter,
    MistralModelsAdapter,
    MistralOcrAdapter,
    MistralRerankAdapter,
)
from api.infrastructure.http.adapters.openai import (
    OpenaiAudioTranscriptionAdapter,
    OpenaiChatCompletionAdapter,
    OpenaiEmbeddingsAdapter,
    OpenaiModelsAdapter,
    OpenaiOcrAdapter,
    OpenaiRerankAdapter,
)
from api.infrastructure.http.adapters.tei import (
    TeiAudioTranscriptionAdapter,
    TeiChatCompletionAdapter,
    TeiEmbeddingsAdapter,
    TeiModelsAdapter,
    TeiOcrAdapter,
    TeiRerankAdapter,
)
from api.infrastructure.http.adapters.vllm import (
    VllmAudioTranscriptionAdapter,
    VllmChatCompletionAdapter,
    VllmEmbeddingsAdapter,
    VllmModelsAdapter,
    VllmOcrAdapter,
    VllmRerankAdapter,
)
from api.utils.variables import EndpointRoute


class Adapters(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    audio_transcriptions: AudioTranscriptionsAdapter
    chat_completions: ChatCompletionsAdapter
    embeddings: EmbeddingsAdapter
    models: ModelsAdapter
    ocr: OcrAdapter
    rerank: RerankAdapter

    def __getitem__(self, key: EndpointRoute) -> EndpointAdapter:
        return getattr(self, key.name.lower())


def build_adapter(
    cost_completion_tokens: float,
    cost_prompt_tokens: float,
    endpoint: EndpointRoute,
    provider: Provider,
    model_environmental_impacts_computer: ModelEnvironmentalImpactsComputer | None = None,
    model_tokenizer: ModelTokenizer | None = None,
) -> EndpointAdapter | UnsupportedProviderEndpointError:
    kwargs = {
        "cost_completion_tokens": cost_completion_tokens,
        "cost_prompt_tokens": cost_prompt_tokens,
        "model_environmental_impacts_computer": model_environmental_impacts_computer,
        "model_tokenizer": model_tokenizer,
        "provider": provider,
    }

    match provider.type:
        case ProviderType.ALBERT:
            adapters = Adapters(
                audio_transcriptions=AlbertAudioTranscriptionAdapter(**kwargs),
                chat_completions=AlbertChatCompletionAdapter(**kwargs),
                embeddings=AlbertEmbeddingsAdapter(**kwargs),
                models=AlbertModelsAdapter(**kwargs),
                ocr=AlbertOcrAdapter(**kwargs),
                rerank=AlbertRerankAdapter(**kwargs),
            )

        case ProviderType.MISTRAL:
            adapters = Adapters(
                audio_transcriptions=MistralAudioTranscriptionAdapter(**kwargs),
                chat_completions=MistralChatCompletionAdapter(**kwargs),
                embeddings=MistralEmbeddingsAdapter(**kwargs),
                models=MistralModelsAdapter(**kwargs),
                ocr=MistralOcrAdapter(**kwargs),
                rerank=MistralRerankAdapter(**kwargs),
            )

        case ProviderType.OPENAI:
            adapters = Adapters(
                audio_transcriptions=OpenaiAudioTranscriptionAdapter(**kwargs),
                chat_completions=OpenaiChatCompletionAdapter(**kwargs),
                embeddings=OpenaiEmbeddingsAdapter(**kwargs),
                models=OpenaiModelsAdapter(**kwargs),
                ocr=OpenaiOcrAdapter(**kwargs),
                rerank=OpenaiRerankAdapter(**kwargs),
            )

        case ProviderType.TEI:
            adapters = Adapters(
                audio_transcriptions=TeiAudioTranscriptionAdapter(**kwargs),
                chat_completions=TeiChatCompletionAdapter(**kwargs),
                embeddings=TeiEmbeddingsAdapter(**kwargs),
                models=TeiModelsAdapter(**kwargs),
                ocr=TeiOcrAdapter(**kwargs),
                rerank=TeiRerankAdapter(**kwargs),
            )

        case ProviderType.VLLM:
            adapters = Adapters(
                audio_transcriptions=VllmAudioTranscriptionAdapter(**kwargs),
                chat_completions=VllmChatCompletionAdapter(**kwargs),
                embeddings=VllmEmbeddingsAdapter(**kwargs),
                models=VllmModelsAdapter(**kwargs),
                ocr=VllmOcrAdapter(**kwargs),
                rerank=VllmRerankAdapter(**kwargs),
            )

    adapter = adapters[endpoint]

    if adapter.TARGET_ENDPOINT_ROUTE is None:
        return UnsupportedProviderEndpointError(endpoint=endpoint, provider_type=provider.type)

    return adapter
