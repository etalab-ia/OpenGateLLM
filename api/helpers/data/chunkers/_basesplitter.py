from abc import ABC, abstractmethod

from langchain_text_splitters import Language


class BaseSplitter(ABC):
    def __init__(self, chunk_min_size: int = 0, metadata: dict | None = None, preset_separators: Language | None = None) -> None:
        self.chunk_min_size = chunk_min_size
        self.metadata = metadata or {}
        self.splitter = None  # this will be set in the child class
        self.preset_separators = preset_separators

    @abstractmethod
    def split(self, content: str) -> list[str]:
        pass
