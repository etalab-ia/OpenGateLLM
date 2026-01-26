from io import BytesIO
import json
import re

from fastapi import HTTPException, UploadFile
import httpx

from api.schemas.parse import ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage

from ._baseparserclient import BaseParserClient


class MarkerParserClient(BaseParserClient):
    """
    Class to interact with the Marker PDF API for document analysis.
    """

    def __init__(self, url: str, headers: dict[str, str], timeout: int, *args, **kwargs) -> None:
        # store configuration but avoid performing network calls in constructor
        self.url = url
        self.headers = headers
        self.timeout = timeout

    async def check_health(self) -> bool:
        """Asynchronously checks the health endpoint of the Marker API.

        Returns True on success, raises an exception for non-2xx responses or network errors.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.url}/health", headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
            except Exception:
                return False
        return True

    def convert_page_range(self, page_range: str, page_count: int) -> list[int]:
        if page_range == "":
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

    async def parse(self, file: UploadFile, force_ocr: bool | None = None, page_range: str = "") -> ParsedDocument:
        file_content = await file.read()

        data = []
        async with httpx.AsyncClient() as client:
            # Create a fresh BytesIO object for each request to avoid stream consumption issues
            files = {"file": (file.filename, BytesIO(file_content), "application/pdf")}
            response = await client.post(
                url=f"{self.url}/marker/upload",
                files=files,
                data={"output_format": "markdown", "page_range": page_range, "force_ocr": force_ocr, "paginate_output": True, "use_llm": False},
                headers=self.headers,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=json.loads(response.text).get("detail", "Parsing failed."))

            response_data = response.json()
            content = response_data.get("output", "")
            images = response_data.get("images", {})
            matches = list(re.finditer(r"\{[0-9]+\}-{48}\n\n", content))
            data = []
            for i in range(len(matches)):
                offset = len(content) if i == len(matches) - 1 else matches[i + 1].span()[0]
                markdown = content[matches[i].span()[1] : offset]
                images_page = {key: f"data:image/jpeg;base64,{value}" for key, value in images.items() if key.startswith(f"_page_{i}_")}
                data.append(
                    ParsedDocumentPage(
                        content=markdown,
                        images=images_page,
                        metadata=ParsedDocumentMetadata(document_name=file.filename, page=i),
                    )
                )

        document = ParsedDocument(data=data)

        return document
