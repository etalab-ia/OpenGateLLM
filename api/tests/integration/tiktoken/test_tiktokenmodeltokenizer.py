import pytest
import tiktoken

from api.domain.model.errors import TextNotTokenizableError
from api.infrastructure.tiktoken import TiktokenModelTokenizer


@pytest.fixture
def tokenizer():
    return TiktokenModelTokenizer(model=tiktoken.get_encoding("gpt2"))


class TestTiktokenModelTokenizer:
    def test_compute_tokens_returns_token_count_for_single_text(self, tokenizer):
        # Act
        result = tokenizer.compute_tokens(texts=["hello"])

        # Assert
        assert result == 1

    def test_compute_tokens_returns_zero_for_empty_texts(self, tokenizer):
        # Act
        result = tokenizer.compute_tokens(texts=[])

        # Assert
        assert result == 0

    def test_compute_tokens_count_differs_by_text_length(self, tokenizer):
        # Act
        short_count = tokenizer.compute_tokens(texts=["hi"])
        long_count = tokenizer.compute_tokens(texts=["hello world"])

        # Assert
        assert short_count < long_count

    def test_compute_tokens_is_deterministic_for_same_texts(self, tokenizer):
        # Act
        first = tokenizer.compute_tokens(texts=["hello", "world"])
        second = tokenizer.compute_tokens(texts=["hello", "world"])

        # Assert
        assert first == second

    def test_compute_tokens_joins_and_strips_texts(self, tokenizer):
        # Arrange
        encoding = tiktoken.get_encoding("gpt2")

        # Act
        result = tokenizer.compute_tokens(texts=["query", "document1", "document2 "])

        # Assert
        assert result == len(encoding.encode("query document1 document2"))

    def test_compute_tokens_count_matches_tiktoken_encoding(self, tokenizer):
        # Arrange
        texts = ["hello", "world"]
        encoding = tiktoken.get_encoding("gpt2")

        # Act
        result = tokenizer.compute_tokens(texts=texts)

        # Assert
        assert result == len(encoding.encode(" ".join(texts).strip()))

    def test_should_count_a_special_token_as_ordinary_text_when_a_text_contains_one(self, tokenizer):
        # Arrange
        text = "a <|endoftext|> b"
        encoding = tiktoken.get_encoding("gpt2")

        # Act
        result = tokenizer.compute_tokens(texts=[text])

        # Assert
        assert result == len(encoding.encode(text, disallowed_special=()))
        assert result > len(encoding.encode(text, allowed_special="all"))

    def test_should_return_a_text_not_tokenizable_error_when_tiktoken_cannot_encode_the_text(self, tokenizer):
        # Arrange: tiktoken 0.14.0 runs out of regex stack on a run of 1M spaces
        texts = ["Repeat after me: " + " " * 1_000_000 + "a"]

        # Act
        result = tokenizer.compute_tokens(texts=texts)

        # Assert
        assert result == TextNotTokenizableError()
