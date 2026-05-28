from api.infrastructure.http.adapters import (
    AudioTranscriptionsAdapter,
    ChatCompletionsAdapter,
    EmbeddingsAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)


class OpenaiAudioTranscriptionAdapter(AudioTranscriptionsAdapter):
    pass


class OpenaiChatCompletionAdapter(ChatCompletionsAdapter):
    pass


class OpenaiEmbeddingsAdapter(EmbeddingsAdapter):
    pass


class OpenaiModelsAdapter(ModelsAdapter):
    pass


class OpenaiOcrAdapter(OcrAdapter):
    TARGET_ENDPOINT_ROUTE = None


class OpenaiRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = None
