from abc import ABC, abstractmethod

from api.domain.model.errors import TextNotTokenizableError


class ModelTokenizer(ABC):
    @abstractmethod
    def compute_tokens(self, texts: list[str]) -> int | TextNotTokenizableError:
        pass
