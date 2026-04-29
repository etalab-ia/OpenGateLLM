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
from api.infrastructure.http.adapters.mistral import (
    MistralAudioTranscriptionAdapter,
    MistralChatCompletionAdapter,
    MistralModelsAdapter,
    MistralRerankAdapter,
)
from api.infrastructure.http.adapters.openai import OpenaiOcrAdapter, OpenaiRerankAdapter
from api.infrastructure.http.adapters.tei import (
    TeiAudioTranscriptionAdapter,
    TeiChatCompletionAdapter,
    TeiModelsAdapter,
    TeiOcrAdapter,
    TeiRerankAdapter,
)
from api.infrastructure.http.adapters.vllm import VllmModelsAdapter, VllmOcrAdapter, VllmRerankAdapter
from api.utils.variables import EndpointRoute


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

    adapters = {
        EndpointRoute.AUDIO_TRANSCRIPTIONS: AudioTranscriptionsAdapter(**kwargs),
        EndpointRoute.CHAT_COMPLETIONS: ChatCompletionsAdapter(**kwargs),
        EndpointRoute.EMBEDDINGS: EmbeddingsAdapter(**kwargs),
        EndpointRoute.MODELS: ModelsAdapter(**kwargs),
        EndpointRoute.OCR: OcrAdapter(**kwargs),
        EndpointRoute.RERANK: RerankAdapter(**kwargs),
    }

    match provider.type:
        case ProviderType.MISTRAL:
            adapters[EndpointRoute.AUDIO_TRANSCRIPTIONS] = MistralAudioTranscriptionAdapter(**kwargs)
            adapters[EndpointRoute.CHAT_COMPLETIONS] = MistralChatCompletionAdapter(**kwargs)
            adapters[EndpointRoute.MODELS] = MistralModelsAdapter(**kwargs)
            adapters[EndpointRoute.RERANK] = MistralRerankAdapter(**kwargs)

        case ProviderType.OPENAI:
            adapters[EndpointRoute.OCR] = OpenaiOcrAdapter(**kwargs)
            adapters[EndpointRoute.RERANK] = OpenaiRerankAdapter(**kwargs)

        case ProviderType.TEI:
            adapters[EndpointRoute.AUDIO_TRANSCRIPTIONS] = TeiAudioTranscriptionAdapter(**kwargs)
            adapters[EndpointRoute.CHAT_COMPLETIONS] = TeiChatCompletionAdapter(**kwargs)
            adapters[EndpointRoute.MODELS] = TeiModelsAdapter(**kwargs)
            adapters[EndpointRoute.OCR] = TeiOcrAdapter(**kwargs)
            adapters[EndpointRoute.RERANK] = TeiRerankAdapter(**kwargs)

        case ProviderType.VLLM:
            adapters[EndpointRoute.MODELS] = VllmModelsAdapter(**kwargs)
            adapters[EndpointRoute.OCR] = VllmOcrAdapter(**kwargs)
            adapters[EndpointRoute.RERANK] = VllmRerankAdapter(**kwargs)

    adapter = adapters[endpoint]

    if adapter.TARGET_ENDPOINT_ROUTE is None:
        return UnsupportedProviderEndpointError(endpoint=endpoint, provider_type=provider.type)

    return adapter
