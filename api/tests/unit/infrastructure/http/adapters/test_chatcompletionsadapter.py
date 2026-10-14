import pytest

from api.domain.provider.entities import ProviderType
from api.infrastructure.http.adapters.chat.vllm import VllmChatCompletionsAdapter
from api.tests.unit.infrastructure.factories import ProviderRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory


@pytest.fixture
def vllm_provider():
    return ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="test-vllm-model", model_total_params=10, model_active_params=5)  # fmt: off


@pytest.fixture
def vllm_chat_completions_adapter(vllm_provider) -> VllmChatCompletionsAdapter:
    return VllmChatCompletionsAdapter(provider=vllm_provider)


class TestVllmChatCompletionsAdapter:
    def test_to_http_request_forces_include_usage_on_streamed_request(self, vllm_chat_completions_adapter):
        # Arrange
        original_request = ProviderRequestFactory(chat_completions=True)
        original_request.payload.stream = True

        # Act
        result = vllm_chat_completions_adapter.to_http_request(original_request)

        # Assert
        assert result.body["stream_options"] == {"include_usage": True}

    def test_to_http_request_forces_include_usage_on_streamed_request_with_stream_options(self, vllm_chat_completions_adapter):
        # Arrange
        original_request = ProviderRequestFactory(chat_completions=True)
        original_request.payload.stream = True
        original_request.payload.stream_options = {"continuous_usage_stats": True, "include_usage": False}

        # Act
        result = vllm_chat_completions_adapter.to_http_request(original_request)

        # Assert
        assert result.body["stream_options"] == {"continuous_usage_stats": True, "include_usage": True}

    def test_to_http_request_does_not_ask_for_the_usage_on_a_non_streamed_request(self, vllm_chat_completions_adapter):
        # Arrange
        original_request = ProviderRequestFactory(chat_completions=True)

        # Act
        result = vllm_chat_completions_adapter.to_http_request(original_request)

        # Assert
        assert "stream_options" not in result.body
