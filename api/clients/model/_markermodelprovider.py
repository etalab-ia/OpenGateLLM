import base64
from io import BytesIO
from json import dumps
import logging
from typing import Any
from urllib.parse import urljoin

from fastapi import HTTPException
import httpx

from api.schemas.ocr import MarkerCreateOCR, MarkerOCR
from api.utils.variables import (
    ENDPOINT__AUDIO_TRANSCRIPTIONS,
    ENDPOINT__CHAT_COMPLETIONS,
    ENDPOINT__EMBEDDINGS,
    ENDPOINT__MODELS,
    ENDPOINT__OCR,
    ENDPOINT__RERANK,
)

from ._basemodelprovider import BaseModelProvider

logger = logging.getLogger(__name__)


class MarkerModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: None,
        ENDPOINT__OCR: "/marker/upload",
        ENDPOINT__RERANK: None,
    }

    def __init__(
        self,
        url: str,
        key: str,
        timeout: int,
        model_name: str,
        model_carbon_footprint_zone: str | None,
        model_carbon_footprint_total_params: int | None,
        model_carbon_footprint_active_params: int | None,
    ) -> None:
        """
        Initialize the Marker model provider and check if the model is available.
        """
        super().__init__(
            model_name=model_name,
            model_carbon_footprint_zone=model_carbon_footprint_zone,
            model_carbon_footprint_total_params=model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=model_carbon_footprint_active_params,
            url=url,
            key=key,
            timeout=timeout,
        )

    async def check_health(self) -> bool:
        url = urljoin(base=self.url, url="/health")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"{self.name} is not reachable: {e}", exc_info=True)
            return False

        return True

    async def get_max_context_length(self) -> int | None:
        return None

    async def _format_request(
        self,
        json: dict | None = None,
        files: dict | None = None,
        data: dict | None = None,
        endpoint: str | None = None,
    ) -> tuple[str, dict[str, str] | None, dict | None, dict | None, dict | None, dict | None]:
        """
        Format a request to a Marker model.
        """
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[endpoint].lstrip("/"))

        if endpoint == ENDPOINT__OCR:
            document_url = json["document"]["document_url"]
            if document_url.startswith("http"):
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(document_url)
                        response.raise_for_status()
                        file_content = response.content
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Failed to download document URL: {str(e)}")  # TODO: replace by custom exception
            else:
                try:
                    file_content = base64.b64decode(document_url.split(",")[1])
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid base64 encoded PDF URL: {str(e)}")  # TODO: replace by custom exception

            if not file_content.startswith(b"%PDF-"):
                raise HTTPException(status_code=400, detail="Invalid document format (only PDF is supported).")  # TODO: replace by custom exception

            files = {"file": (f"{request_id}.pdf", BytesIO(file_content), "application/pdf")}
            data = MarkerCreateOCR(**json).model_dump()

            additional_data = {"usage_info": {"doc_size_bytes": len(file_content)}}

        return url, json, files, data, additional_data

    def _format_response(
        self,
        request_id: str,
        json: dict,
        response: httpx.Response,
        endpoint: str,
        additional_data: dict[str, Any] | None = None,
        request_latency: float = 0.0,
    ) -> httpx.Response:
        if additional_data is None:
            additional_data = {}

        content_type = response.headers.get("Content-Type", "")
        if content_type != "application/json":
            return response

        data = response.json()

        usage = self._get_usage(json=json, data=data, stream=False, endpoint=endpoint, request_latency=request_latency)
        request_id = usage.details[-1].id if usage and usage.details else request_id
        additional_data.update({"model": self.name, "id": request_id})

        if endpoint == ENDPOINT__OCR:
            data = MarkerOCR(**data, include_image_base64=json.get("include_image_base64"), usage_info=additional_data.get("usage_info", {}))

        response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response
