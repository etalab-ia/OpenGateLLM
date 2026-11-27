import asyncio

from huggingface_hub import get_hf_file_metadata, hf_hub_url
from huggingface_hub.errors import (
    EntryNotFoundError,
    HFValidationError,
    OfflineModeIsEnabled,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from tokenizers import Tokenizer

from api.domain.provider import TokenizerRegistry
from api.domain.provider.errors import TokenizerNotLoadableError

TOKENIZER_FILE = "tokenizer.json"


class HuggingFaceTokenizerRegistry(TokenizerRegistry):
    """
    Loads tokenizers from the Hugging Face Hub and keeps them in memory for the life of the process.

    There is one registry per worker process, so a tokenizer validated on one gunicorn worker is loaded again on another
    the first time that worker uses it (from the Hub disk cache under `HF_HOME` when it is there).

    The cache key includes the token: a gated tokenizer loaded with one provider's token must not validate another
    provider that has no valid token. The Hub disk cache is shared by every token, so the first load of each key asks
    the Hub whether this token may read the file before the cache is used. A failed load is not cached.
    """

    def __init__(self):
        self._tokenizers: dict[tuple[str, str | None], Tokenizer] = {}
        self._locks: dict[tuple[str, str | None], asyncio.Lock] = {}

    async def get(self, tokenizer_name: str, hf_token: str | None) -> Tokenizer | TokenizerNotLoadableError:
        key = (tokenizer_name, hf_token)
        if key in self._tokenizers:
            return self._tokenizers[key]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if key in self._tokenizers:
                return self._tokenizers[key]
            try:
                tokenizer = await asyncio.to_thread(self._load, tokenizer_name, hf_token)
            except (RepositoryNotFoundError, RevisionNotFoundError, EntryNotFoundError, HFValidationError) as error:
                return TokenizerNotLoadableError(tokenizer_name=tokenizer_name, detail=type(error).__name__)
            self._tokenizers[key] = tokenizer
            return tokenizer

    @staticmethod
    def _load(tokenizer_name: str, hf_token: str | None) -> Tokenizer:
        try:
            get_hf_file_metadata(
                hf_hub_url(tokenizer_name, TOKENIZER_FILE),
                token=hf_token or False,
            )
        except OfflineModeIsEnabled:
            pass
        return Tokenizer.from_pretrained(tokenizer_name, token=hf_token)
