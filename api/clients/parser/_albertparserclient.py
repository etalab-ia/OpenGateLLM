from io import BytesIO
import json

from fastapi import HTTPException, UploadFile
import httpx

from api.schemas.parse import ParsedDocument

from ._baseparserclient import BaseParserClient


class AlbertParserClient(BaseParserClient):
    """
    Class to interact with the Albert PDF API for document analysis.
    """

    URL = "https://albert.api.etalab.gouv.fr"

    def __init__(self, headers: dict[str, str], timeout: int, url: str | None = None, *args, **kwargs) -> None:
        # store configuration but avoid performing network calls in constructor
        self.url = url or self.URL
        self.headers = headers
        self.timeout = timeout

    async def check_health(self) -> bool:
        """Asynchronously checks the health endpoint of the Albert API.

        Returns True on success, raises an exception for non-2xx responses or network errors.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.url}/health", headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
            except Exception:
                return False
        return True

    async def parse(self, file: UploadFile, force_ocr: bool | None = None, page_range: str = "") -> ParsedDocument:
        file_content = await file.read()

        async with httpx.AsyncClient() as client:
            files = {"file": (file.filename, BytesIO(file_content), "application/pdf")}
            response = await client.post(
                url=f"{self.url}/v1/parse-beta",
                files=files,
                data={"force_ocr": force_ocr, "page_range": page_range},
                headers=self.headers,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                try:
                    detail = json.loads(response.text).get("detail", "Parsing failed.")
                except Exception:
                    detail = response.text
                raise HTTPException(status_code=response.status_code, detail=detail)

            result = response.json()

        document = ParsedDocument(data=result["data"])

        return document
