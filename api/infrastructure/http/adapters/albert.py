from api.infrastructure.http.adapters import (
    AudioTranscriptionsAdapter,
    ChatCompletionsAdapter,
    EmbeddingsAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)


class AlbertAudioTranscriptionAdapter(AudioTranscriptionsAdapter):
    pass


class AlbertChatCompletionAdapter(ChatCompletionsAdapter):
    pass


class AlbertEmbeddingsAdapter(EmbeddingsAdapter):
    pass


class AlbertModelsAdapter(ModelsAdapter):
    pass


class AlbertOcrAdapter(OcrAdapter):
    pass


class AlbertRerankAdapter(RerankAdapter):
    pass
