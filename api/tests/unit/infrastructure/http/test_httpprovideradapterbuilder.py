import pytest

from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import UnsupportedProviderEndpointError
from api.infrastructure.http import HttpProviderAdapterBuilder
from api.infrastructure.http.adapters.audio import AudioTranscriptionsAdapter
from api.infrastructure.http.adapters.audio.mistral import MistralAudioTranscriptionsAdapter
from api.infrastructure.http.adapters.chat import ChatCompletionsAdapter
from api.infrastructure.http.adapters.chat.mistral import MistralChatCompletionsAdapter
from api.infrastructure.http.adapters.embeddings import EmbeddingsAdapter
from api.infrastructure.http.adapters.models import ModelsAdapter
from api.infrastructure.http.adapters.models.mistral import MistralModelsAdapter
from api.infrastructure.http.adapters.models.tei import TeiModelsAdapter
from api.infrastructure.http.adapters.models.vllm import VllmModelsAdapter
from api.infrastructure.http.adapters.ocr import OcrAdapter
from api.infrastructure.http.adapters.rerank import RerankAdapter
from api.infrastructure.http.adapters.rerank.tei import TeiRerankAdapter
from api.infrastructure.http.adapters.rerank.vllm import VllmRerankAdapter
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def http_provider_adapter_builder() -> HttpProviderAdapterBuilder:
    return HttpProviderAdapterBuilder()


class TestHttpProviderAdapterBuilder:
    def test_should_pass_provider_to_adapter(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act
        result = http_provider_adapter_builder.build(endpoint=EndpointRoute.RERANK, provider=provider)

        # Assert
        assert isinstance(result, VllmRerankAdapter)
        assert result.provider == provider

    def test_should_return_default_audio_transcriptions_adapter_for_albert_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, AudioTranscriptionsAdapter)

    def test_should_return_default_chat_completions_adapter_for_albert_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.CHAT_COMPLETIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, ChatCompletionsAdapter)

    def test_should_return_default_embeddings_adapter_for_albert_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.EMBEDDINGS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, EmbeddingsAdapter)

    def test_should_return_default_models_adapter_for_albert_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.MODELS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, ModelsAdapter)

    def test_should_return_default_ocr_adapter_for_albert_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.OCR,
            provider=provider,
        )

        # Assert
        assert isinstance(result, OcrAdapter)

    def test_should_return_default_rerank_adapter_for_albert_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.RERANK,
            provider=provider,
        )

        # Assert
        assert isinstance(result, RerankAdapter)

    def test_should_return_mistral_audio_transcriptions_adapter_for_mistral_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, MistralAudioTranscriptionsAdapter)

    def test_should_return_mistral_chat_completions_adapter_for_mistral_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.CHAT_COMPLETIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, MistralChatCompletionsAdapter)

    def test_should_return_mistral_models_adapter_for_mistral_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.MODELS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, MistralModelsAdapter)

    def test_should_return_mistral_embeddings_adapter_for_mistral_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.EMBEDDINGS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, EmbeddingsAdapter)

    def test_should_return_mistral_ocr_adapter_for_mistral_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.OCR,
            provider=provider,
        )

        # Assert
        assert isinstance(result, OcrAdapter)

    def test_should_return_openai_audio_transcriptions_adapter_for_openai_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.OPENAI, url="https://openai.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, AudioTranscriptionsAdapter)

    def test_should_return_openai_chat_completions_adapter_for_openai_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.OPENAI, url="https://openai.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.CHAT_COMPLETIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, ChatCompletionsAdapter)

    def test_should_return_openai_embeddings_adapter_for_openai_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.OPENAI, url="https://openai.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.EMBEDDINGS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, EmbeddingsAdapter)

    def test_should_return_openai_models_adapter_for_openai_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.OPENAI, url="https://openai.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.MODELS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, ModelsAdapter)

    def test_should_return_tei_models_adapter_for_tei_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.TEI, url="https://tei.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.MODELS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, TeiModelsAdapter)

    def test_should_return_tei_rerank_adapter_for_tei_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.TEI, url="https://tei.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.RERANK,
            provider=provider,
        )

        # Assert
        assert isinstance(result, TeiRerankAdapter)

    def test_should_return_tei_embeddings_adapter_for_tei_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.TEI, url="https://tei.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.EMBEDDINGS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, EmbeddingsAdapter)

    def test_should_return_vllm_models_adapter_for_vllm_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.MODELS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, VllmModelsAdapter)

    def test_should_return_vllm_rerank_adapter_for_vllm_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.RERANK,
            provider=provider,
        )

        # Assert
        assert isinstance(result, VllmRerankAdapter)

    def test_should_return_vllm_chat_completions_adapter_for_vllm_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.CHAT_COMPLETIONS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, ChatCompletionsAdapter)

    def test_should_return_vllm_embeddings_adapter_for_vllm_provider(self, http_provider_adapter_builder: HttpProviderAdapterBuilder):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=EndpointRoute.EMBEDDINGS,
            provider=provider,
        )

        # Assert
        assert isinstance(result, EmbeddingsAdapter)

    @pytest.mark.parametrize(
        "provider_type,endpoint",
        [
            (ProviderType.MISTRAL, EndpointRoute.RERANK),
            (ProviderType.OPENAI, EndpointRoute.OCR),
            (ProviderType.OPENAI, EndpointRoute.RERANK),
            (ProviderType.TEI, EndpointRoute.AUDIO_TRANSCRIPTIONS),
            (ProviderType.TEI, EndpointRoute.CHAT_COMPLETIONS),
            (ProviderType.TEI, EndpointRoute.OCR),
            (ProviderType.VLLM, EndpointRoute.OCR),
        ],
    )
    def test_should_return_unsupported_provider_endpoint_error_when_adapter_is_not_found(
        self,
        http_provider_adapter_builder: HttpProviderAdapterBuilder,
        provider_type: ProviderType,
        endpoint: EndpointRoute,
    ):
        # Arrange
        provider = ProviderFactory(type=provider_type, url="https://provider.test")

        # Act
        result = http_provider_adapter_builder.build(
            endpoint=endpoint,
            provider=provider,
        )

        # Assert
        assert isinstance(result, UnsupportedProviderEndpointError)
        assert result.endpoint == endpoint
        assert result.provider_type == provider_type
