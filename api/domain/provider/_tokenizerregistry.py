from abc import ABC, abstractmethod

from tokenizers import Tokenizer

from api.domain.provider.errors import TokenizerNotLoadableError


class TokenizerRegistry(ABC):
    @abstractmethod
    async def get(self, tokenizer_name: str, hf_token: str | None) -> Tokenizer | TokenizerNotLoadableError:
        pass
