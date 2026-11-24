import asyncio
from pathlib import Path

import tiktoken
from tokenizers import Tokenizer

from api.domain.model import TIKTOKEN_TOKENIZER_NAMES, ModelTokenizer, ModelTokenizerLoader
from api.domain.model.errors import ModelTokenizerNotLoadableError
from api.infrastructure.huggingface import HuggingFaceModelTokenizer
from api.infrastructure.tiktoken import TiktokenModelTokenizer


class CachedModelTokenizerLoader(ModelTokenizerLoader):
    def __init__(self, default_tokenizer: str):
        self.default_tokenizer = default_tokenizer
        self._tokenizers: dict[str, ModelTokenizer] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def load(self, tokenizer: str | None) -> ModelTokenizer | ModelTokenizerNotLoadableError:
        name = self.default_tokenizer if tokenizer is None else tokenizer

        if name in self._tokenizers:
            return self._tokenizers[name]

        lock = self._locks.setdefault(name, asyncio.Lock())
        async with lock:
            if name in self._tokenizers:
                return self._tokenizers[name]

            try:
                # loading reads a file or downloads from the Hugging Face Hub: keep it off the event loop
                model_tokenizer = await asyncio.to_thread(self._build, name)
            except Exception as e:
                # a failed load is not cached: the Hub may be back on the next try
                return ModelTokenizerNotLoadableError(tokenizer=name, detail=str(e))

            self._tokenizers[name] = model_tokenizer
            return model_tokenizer

    @staticmethod
    def _build(name: str) -> ModelTokenizer:
        if name in TIKTOKEN_TOKENIZER_NAMES:
            return TiktokenModelTokenizer(model=tiktoken.get_encoding(name.removeprefix("tiktoken_")))

        if Path(name).is_file():
            return HuggingFaceModelTokenizer(model=Tokenizer.from_file(name))

        return HuggingFaceModelTokenizer(model=Tokenizer.from_pretrained(name))
