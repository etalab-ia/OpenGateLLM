from abc import ABC, abstractmethod

from api.domain.model._modeltokenizer import ModelTokenizer
from api.domain.model.errors import ModelTokenizerNotLoadableError


class ModelTokenizerLoader(ABC):
    @abstractmethod
    async def load(self, tokenizer: str | None) -> ModelTokenizer | ModelTokenizerNotLoadableError:
        """Return the tokenizer named by a router, or the default one when `tokenizer` is None."""
