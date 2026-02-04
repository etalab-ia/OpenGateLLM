from abc import ABC, abstractmethod
import importlib

from fastapi import UploadFile

from api.schemas.core.configuration import ParserType
from api.schemas.parse import ParsedDocument


class BaseParserClient(ABC):
    @staticmethod
    def import_module(type: ParserType) -> "type[BaseParserClient]":
        """
        Static method to import a subclass of BaseParserClient.

        Args:
            type(str): The type of parser client to import.

        Returns:
            Type[BaseParserClient]: The subclass of BaseParserClient.
        """
        module = importlib.import_module(f"api.clients.parser._{type.value}parserclient")
        return getattr(module, f"{type.capitalize()}ParserClient")

    def convert_page_range(self, page_range: str, page_count: int) -> list[int]:
        if not page_range:
            return [i for i in range(page_count)]

        page_ranges = page_range.split(",")
        pages = []
        for page_range in page_ranges:
            page_range = page_range.split("-")
            if len(page_range) == 1:
                pages.append(int(page_range[0]))
            else:
                for i in range(int(page_range[0]), int(page_range[1]) + 1):
                    pages.append(i)

        pages = list(set(pages))

        return pages

    @abstractmethod
    def check_health(self) -> bool:
        pass

    @abstractmethod
    def parse(self, file: UploadFile, force_ocr: bool | None = None, page_range: str = "") -> ParsedDocument:
        pass
