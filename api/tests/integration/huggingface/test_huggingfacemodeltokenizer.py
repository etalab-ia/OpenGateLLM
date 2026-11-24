import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from api.infrastructure.huggingface import HuggingFaceModelTokenizer


@pytest.fixture
def tokenizer():
    model = Tokenizer(WordLevel(vocab={"[UNK]": 0, "hello": 1, "world": 2}, unk_token="[UNK]"))
    model.pre_tokenizer = Whitespace()
    return HuggingFaceModelTokenizer(model=model)


class TestHuggingFaceModelTokenizer:
    def test_should_return_the_token_count_when_a_text_is_given(self, tokenizer):
        # Act
        result = tokenizer.compute_tokens(texts=["hello world"])

        # Assert
        assert result == 2

    def test_should_join_the_texts_when_several_are_given(self, tokenizer):
        # Act
        result = tokenizer.compute_tokens(texts=["hello", "world", "hello"])

        # Assert
        assert result == 3

    def test_should_return_zero_when_no_text_is_given(self, tokenizer):
        # Act
        result = tokenizer.compute_tokens(texts=[])

        # Assert
        assert result == 0
