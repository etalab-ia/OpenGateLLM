from langchain_text_splitters import Language
from langchain_text_splitters import RecursiveCharacterTextSplitter as LangChainRecursiveCharacterTextSplitter

from ._basesplitter import BaseSplitter


class RecursiveCharacterTextSplitter(BaseSplitter):
    def __init__(
        self,
        chunk_min_size: int = 0,
        metadata: dict | None = None,
        preset_separators: Language | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(chunk_min_size=chunk_min_size, metadata=metadata, preset_separators=preset_separators)
        if preset_separators:
            kwargs.pop("separators")
            kwargs.pop("is_separator_regex")
            self.splitter = LangChainRecursiveCharacterTextSplitter.from_language(language=self.preset_separators, *args, **kwargs)
        else:
            self.splitter = LangChainRecursiveCharacterTextSplitter(*args, **kwargs)

    def split(self, content: str) -> list[str]:
        chunks = self.splitter.split_text(content)
        chunks = [chunk for chunk in chunks if len(chunk) >= self.chunk_min_size]

        return chunks
