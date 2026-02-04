from langchain_text_splitters import Language

from ._basesplitter import BaseSplitter


class NoSplitter(BaseSplitter):
    def __init__(
        self,
        chunk_min_size: int = 0,
        metadata: dict | None = None,
        preset_separators: Language | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(chunk_min_size=chunk_min_size, metadata=metadata, preset_separators=preset_separators)

    def split(self, content: str) -> list[str]:
        chunks = [content] if len(content) >= self.chunk_min_size else []

        return chunks
