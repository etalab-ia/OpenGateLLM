import asyncio
from pathlib import Path

import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.infrastructure.huggingface import HuggingFaceModelTokenizer
from api.infrastructure.modeltokenizer import CachedModelTokenizerLoader
from api.infrastructure.tiktoken import TiktokenModelTokenizer


@pytest.fixture
def tokenizer_file(tmp_path) -> Path:
    model = Tokenizer(WordLevel(vocab={"[UNK]": 0, "hello": 1}, unk_token="[UNK]"))
    model.pre_tokenizer = Whitespace()
    path = tmp_path / "tokenizer.json"
    model.save(str(path))
    return path


@pytest.fixture
def loader():
    return CachedModelTokenizerLoader(default_tokenizer="tiktoken_gpt2")


class TestCachedModelTokenizerLoader:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_load_the_tiktoken_encoding_when_the_name_is_a_tiktoken_literal(self, loader):
        # Act
        result = await loader.load("tiktoken_o200k_base")

        # Assert
        assert isinstance(result, TiktokenModelTokenizer)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_load_the_default_tokenizer_when_no_tokenizer_is_given(self, loader):
        # Act
        result = await loader.load(None)

        # Assert
        assert result is await loader.load("tiktoken_gpt2")

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_load_a_hugging_face_tokenizer_when_the_name_is_a_local_file(self, loader, tokenizer_file):
        # Act
        result = await loader.load(str(tokenizer_file))

        # Assert
        assert isinstance(result, HuggingFaceModelTokenizer)
        assert result.compute_tokens(texts=["hello hello"]) == 2

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_return_the_same_tokenizer_when_it_is_loaded_twice(self, loader, tokenizer_file):
        # Act
        first = await loader.load(str(tokenizer_file))
        second = await loader.load(str(tokenizer_file))

        # Assert
        assert first is second

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_load_a_tokenizer_once_when_requested_concurrently(self, loader, tokenizer_file):
        # Act
        results = await asyncio.gather(*[loader.load(str(tokenizer_file)) for _ in range(5)])

        # Assert
        assert all(result is results[0] for result in results)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_return_an_error_when_the_local_file_is_not_a_tokenizer(self, loader, tmp_path):
        # Arrange
        invalid_file = tmp_path / "tokenizer.json"
        invalid_file.write_text("not a tokenizer")

        # Act
        result = await loader.load(str(invalid_file))

        # Assert
        assert isinstance(result, ModelTokenizerNotLoadableError)
        assert result.tokenizer == str(invalid_file)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_return_an_error_without_caching_it_when_the_hugging_face_id_is_unknown(self, loader, monkeypatch):
        # Arrange
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")

        # Act
        result = await loader.load("unknown-org/unknown-model")

        # Assert
        assert isinstance(result, ModelTokenizerNotLoadableError)
        assert "unknown-org/unknown-model" not in loader._tokenizers

    @pytest.mark.asyncio(loop_scope="session")
    async def test_should_treat_an_unlisted_tiktoken_name_as_a_hugging_face_id(self, loader, monkeypatch):
        # Arrange
        monkeypatch.setenv("HF_HUB_OFFLINE", "1")

        # Act
        result = await loader.load("tiktoken_foo")

        # Assert
        assert isinstance(result, ModelTokenizerNotLoadableError)
