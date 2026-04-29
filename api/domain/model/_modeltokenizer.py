from abc import ABC, abstractmethod


class ModelTokenizer(ABC):
    @abstractmethod
    def encode(self, text: str) -> int:
        pass
