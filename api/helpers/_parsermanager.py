import asyncio
import logging
from pathlib import Path

from fastapi import UploadFile
from html_to_markdown import convert_to_markdown
import pymupdf
import pymupdf4llm

from api.schemas.core.documents import FileType
from api.utils.exceptions import UnsupportedFileTypeException

logger = logging.getLogger(__name__)


class ParserManager:
    EXTENSION_MAP: dict[str, FileType] = {
        ".pdf": FileType.PDF,
        ".html": FileType.HTML,
        ".htm": FileType.HTML,
        ".md": FileType.MD,
        ".markdown": FileType.MD,
        ".txt": FileType.TXT,
        ".text": FileType.TXT,
    }

    VALID_CONTENT_TYPES: dict[FileType, set[str]] = {
        FileType.PDF: {
            "application/pdf",
            "application/octet-stream",
        },
        FileType.HTML: {
            "text/html",
            "text/plain",
            "application/html",
            "application/octet-stream",
        },
        FileType.MD: {
            "text/markdown",
            "text/x-markdown",
            "text/plain",
            "application/markdown",
            "application/octet-stream",
        },
        FileType.TXT: {
            "text/plain",
            "text/txt",
            "application/octet-stream",
        },
    }

    def __init__(self, max_concurrent: int = 10):
        self.conversion_semaphore = asyncio.Semaphore(value=max_concurrent)

    async def parse(self, file: UploadFile) -> str:
        file_type = self.check_file_type(file=file)
        content = None

        match file_type:
            case FileType.PDF:
                async with self.conversion_semaphore:
                    file_content = await file.read()
                    doc = pymupdf.open(stream=file_content, filetype="pdf")
                    content = await asyncio.to_thread(pymupdf4llm.to_markdown, doc)

            case FileType.HTML:
                file_content = await self._read_content(file=file)
                content = convert_to_markdown(file_content).strip()

            case FileType.MD:
                file_content = await self._read_content(file=file)
                content = file_content.strip()

            case FileType.TXT:
                file_content = await self._read_content(file=file)
                content = file_content.strip()

        return content

    def check_file_type(self, file: UploadFile, type: FileType | None = None) -> FileType:
        """
        Detect file type by extension, then check content-type.
        """
        try:
            filename = file.filename or ""
            extension = Path(filename).suffix.lower()
            content_type = file.content_type or ""
        except Exception:
            raise UnsupportedFileTypeException()

        # detect type by extension and content-type
        detected_type = None
        if extension in self.EXTENSION_MAP:
            file_type = self.EXTENSION_MAP[extension]
            if content_type in self.VALID_CONTENT_TYPES[file_type]:
                detected_type = file_type
        else:
            # detect type only by content-type (less robust because it stops after first match)
            for file_type, valid_content_types in self.VALID_CONTENT_TYPES.items():
                if content_type in valid_content_types and content_type != "application/octet-stream":
                    detected_type = file_type

        if detected_type is None:
            logger.debug(f"Failed to detect file type: extension={extension}, content_type={content_type}")
            raise UnsupportedFileTypeException()

        if type is not None and detected_type != type:
            raise UnsupportedFileTypeException(f"File must be a {type.value} file.")

        return detected_type

    @staticmethod
    async def _read_content(file: UploadFile) -> str:
        content_bytes = await file.read()
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content_bytes.decode("latin-1")
            except UnicodeDecodeError as e:
                logger.debug(msg=f"Encoding problem detected for {file.filename}: {e}")
                content = content_bytes.decode("utf-8", errors="replace")

        await file.seek(0)

        return content
