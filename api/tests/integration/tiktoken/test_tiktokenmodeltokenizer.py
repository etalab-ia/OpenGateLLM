import pytest
import tiktoken

from api.infrastructure.tiktoken import TiktokenModelTokenizer


@pytest.fixture
def tokenizer():
    return TiktokenModelTokenizer(model=tiktoken.get_encoding("gpt2"))


class TestTiktokenModelTokenizer:
    def test_encode_returns_same_tokens_as_underlying_encoding(self, tokenizer):
        # Act
        result = tokenizer.encode("hello")

        # Assert
        assert result == [31373]

    def test_encode_returns_empty_list_for_empty_string(self, tokenizer):
        # Act
        result = tokenizer.encode("")

        # Assert
        assert result == []

    def test_encode_token_count_differs_by_text_length(self, tokenizer):
        # Act
        short_tokens = tokenizer.encode("hi")
        long_tokens = tokenizer.encode("hello world")

        # Assert
        assert len(short_tokens) < len(long_tokens)

    def test_encode_is_deterministic_for_same_text(self, tokenizer):
        # Act
        first = tokenizer.encode("hello world")
        second = tokenizer.encode("hello world")

        # Assert
        assert first == second

    def test_encode_token_count_matches_tiktoken_encoding(self, tokenizer):
        # Arrange
        text = "hello world"
        encoding = tiktoken.get_encoding("gpt2")

        # Act
        result = tokenizer.encode(text)

        # Assert
        assert len(result) == len(encoding.encode(text))
