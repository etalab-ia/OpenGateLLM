import pytest

from api.infrastructure.http.adapters.chat import ChatCompletionsAdapter
from api.tests.unit.infrastructure.factories import ProviderRequestFactory
from api.tests.unit.use_case.factories import ProviderFactory


@pytest.fixture
def chat_completions_adapter() -> ChatCompletionsAdapter:
    return ChatCompletionsAdapter(provider=ProviderFactory())


class TestChatCompletionsAdapter:
    def test_to_http_request_forces_include_usage_on_streamed_request(self, chat_completions_adapter):
        # Arrange
        original_request = ProviderRequestFactory(chat_completions=True)
        original_request.payload.stream = True

        # Act
        result = chat_completions_adapter.to_http_request(original_request)

        # Assert
        assert result.body["stream_options"] == {"include_usage": True}

    def test_to_http_request_forces_include_usage_on_streamed_request_with_stream_options(self, chat_completions_adapter):
        # Arrange
        original_request = ProviderRequestFactory(chat_completions=True)
        original_request.payload.stream = True
        original_request.payload.stream_options = {"continuous_usage_stats": True, "include_usage": False}

        # Act
        result = chat_completions_adapter.to_http_request(original_request)

        # Assert
        assert result.body["stream_options"] == {"continuous_usage_stats": True, "include_usage": True}

    def test_to_http_request_does_not_ask_for_the_usage_on_a_non_streamed_request(self, chat_completions_adapter):
        # Arrange
        original_request = ProviderRequestFactory(chat_completions=True)

        # Act
        result = chat_completions_adapter.to_http_request(original_request)

        # Assert
        assert "stream_options" not in result.body
