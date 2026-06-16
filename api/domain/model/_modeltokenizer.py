from abc import ABC, abstractmethod


class ModelTokenizer(ABC):
    @abstractmethod
    def compute_tokens(self, texts: list[str]) -> int:
        pass
