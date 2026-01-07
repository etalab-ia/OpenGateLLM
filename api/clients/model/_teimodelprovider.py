from json import dumps
import logging
from urllib.parse import urljoin

import httpx

from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import RequestContent
from api.schemas.rerank import CreateRerank, Reranks
from api.utils.context import generate_request_id, request_context
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


class TeiModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/info",
        ENDPOINT__OCR: None,
        ENDPOINT__RERANK: "/rerank",
    }

    def __init__(
        self,
        url: str,
        key: str,
        timeout: int,
        model_name: str,
        model_hosting_zone: str | None,
        model_total_params: int | None,
        model_active_params: int | None,
    ) -> None:
        """
        Initialize the TEI model client and check if the model is available.
        """
        super().__init__(
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_hosting_zone=model_hosting_zone,
            model_total_params=model_total_params,
            model_active_params=model_active_params,
        )

    async def get_max_context_length(self) -> int | None:
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[ENDPOINT__MODELS].lstrip("/"))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error getting max context length for {self.name}: {e}", exc_info=True)
            raise AssertionError(f"Model is not reachable ({e}).")

        data = response.json()
        assert self.name == data["model_id"], f"Model not found ({self.name})."
        max_context_length = data.get("max_input_length")
        return max_context_length

    def _format_request(self, request_content: RequestContent) -> RequestContent:
        """
        Format a request to a TEI model, overridden base class method to add TEI specific format request.
        """
        if "model" in request_content.json:
            request_content.json["model"] = self.name

        if "model" in request_content.form:
            request_content.form["model"] = self.name

        if request_content.endpoint.endswith(ENDPOINT__RERANK):
            request_content.json = CreateRerank(**request_content.json).format(provider=ProviderType.TEI).model_dump()
            request_content.additional_data["top_n"] = request_content.json.get("top_n")

        return request_content

    def _format_response(self, request_content: RequestContent, response: httpx.Response, request_latency: float = 0.0) -> httpx.Response:
        """
        Format a response from a TEI model, overridden base class method to convert TEI reranking response to a standard response.
        """

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            response_data = response.json()
            top_n = request_content.additional_data.pop("top_n")
            if request_content.endpoint == ENDPOINT__RERANK:
                response_data = Reranks.build_from(provider=ProviderType.TEI, response_data=response_data, top_n=top_n).model_dump()

            usage = self._get_usage(request_content=request_content, response_data=response_data, stream=False, request_latency=request_latency)

            if request_context.get().id is None:
                request_id = response_data.get("id", generate_request_id())
                request_context.get().id = request_id
            else:
                request_id = request_context.get().id

            additional_data = request_content.additional_data
            additional_data.update({"model": request_content.model, "id": request_id, "usage": usage.model_dump()})
            response.update(additional_data)

            response = httpx.Response(status_code=response.status_code, content=dumps(response))

        return response
