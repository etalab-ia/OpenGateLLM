from unittest.mock import Mock

import pytest

from api.domain.provider.entities import ProviderType
from api.domain.provider.errors import UnsupportedProviderEndpointError
from api.infrastructure.http.adapters import (
    AudioTranscriptionsAdapter,
    ChatCompletionsAdapter,
    EmbeddingsAdapter,
    ModelsAdapter,
    OcrAdapter,
    RerankAdapter,
)
from api.infrastructure.http.adapters.mistral import (
    MistralAudioTranscriptionAdapter,
    MistralChatCompletionAdapter,
    MistralModelsAdapter,
)
from api.infrastructure.http.adapters.tei import TeiModelsAdapter, TeiRerankAdapter
from api.infrastructure.http.adapters.utils import build_adapter
from api.infrastructure.http.adapters.vllm import VllmModelsAdapter, VllmRerankAdapter
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


@pytest.fixture
def cost_completion_tokens() -> float:
    return 0.5


@pytest.fixture
def cost_prompt_tokens() -> float:
    return 0.1


@pytest.fixture
def model_environmental_impacts_computer() -> Mock:
    return Mock()


@pytest.fixture
def model_tokenizer() -> Mock:
    return Mock()


class TestBuildAdapter:
    def test_should_pass_provider_and_costs_to_adapter(
        self,
        cost_completion_tokens: float,
        cost_prompt_tokens: float,
        model_environmental_impacts_computer: Mock,
        model_tokenizer: Mock,
    ):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act
        result = build_adapter(
            cost_completion_tokens=cost_completion_tokens,
            cost_prompt_tokens=cost_prompt_tokens,
            endpoint=EndpointRoute.RERANK,
            provider=provider,
            model_environmental_impacts_computer=model_environmental_impacts_computer,
            model_tokenizer=model_tokenizer,
        )

        # Assert
        assert isinstance(result, VllmRerankAdapter)
        assert result.provider == provider
        assert result.cost_completion_tokens == cost_completion_tokens
        assert result.cost_prompt_tokens == cost_prompt_tokens
        assert result.model_environmental_impacts_computer == model_environmental_impacts_computer
        assert result.model_tokenizer == model_tokenizer

    def test_should_return_default_adapters_for_albert_provider(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.ALBERT, url="https://albert.test")

        # Act / Assert
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS, provider=provider),
            AudioTranscriptionsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.CHAT_COMPLETIONS, provider=provider),
            ChatCompletionsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.EMBEDDINGS, provider=provider),
            EmbeddingsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.MODELS, provider=provider),
            ModelsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.OCR, provider=provider),
            OcrAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.RERANK, provider=provider),
            RerankAdapter,
        )

    def test_should_return_mistral_specific_adapters_for_mistral_provider(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test")

        # Act / Assert
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS, provider=provider),
            MistralAudioTranscriptionAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.CHAT_COMPLETIONS, provider=provider),
            MistralChatCompletionAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.MODELS, provider=provider),
            MistralModelsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.EMBEDDINGS, provider=provider),
            EmbeddingsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.OCR, provider=provider),
            OcrAdapter,
        )

    def test_should_return_openai_specific_adapters_for_openai_provider(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.OPENAI, url="https://openai.test")

        # Act / Assert
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS, provider=provider),
            AudioTranscriptionsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.CHAT_COMPLETIONS, provider=provider),
            ChatCompletionsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.EMBEDDINGS, provider=provider),
            EmbeddingsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.MODELS, provider=provider),
            ModelsAdapter,
        )

    def test_should_return_tei_specific_adapters_for_tei_provider(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.TEI, url="https://tei.test")

        # Act / Assert
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.MODELS, provider=provider),
            TeiModelsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.RERANK, provider=provider),
            TeiRerankAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.EMBEDDINGS, provider=provider),
            EmbeddingsAdapter,
        )

    def test_should_return_vllm_specific_adapters_for_vllm_provider(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test")

        # Act / Assert
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.MODELS, provider=provider),
            VllmModelsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.RERANK, provider=provider),
            VllmRerankAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.CHAT_COMPLETIONS, provider=provider),
            ChatCompletionsAdapter,
        )
        assert isinstance(
            build_adapter(cost_completion_tokens=0, cost_prompt_tokens=0, endpoint=EndpointRoute.EMBEDDINGS, provider=provider),
            EmbeddingsAdapter,
        )

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
    def test_should_return_unsupported_provider_endpoint_error_when_target_route_is_none(self, provider_type: ProviderType, endpoint: EndpointRoute):
        # Arrange
        provider = ProviderFactory(type=provider_type, url="https://provider.test")

        # Act
        result = build_adapter(
            cost_completion_tokens=0,
            cost_prompt_tokens=0,
            endpoint=endpoint,
            provider=provider,
        )

        # Assert
        assert isinstance(result, UnsupportedProviderEndpointError)
        assert result.endpoint == endpoint
        assert result.provider_type == provider_type
