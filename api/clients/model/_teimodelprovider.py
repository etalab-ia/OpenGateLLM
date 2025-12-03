from json import dumps
import logging
from typing import Any
from urllib.parse import urljoin

import httpx

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
        model_carbon_footprint_zone: str | None,
        model_carbon_footprint_total_params: int | None,
        model_carbon_footprint_active_params: int | None,
    ) -> None:
        """
        Initialize the TEI model client and check if the model is available.
        """
        super().__init__(
            url=url,
            key=key,
            timeout=timeout,
            model_name=model_name,
            model_carbon_footprint_zone=model_carbon_footprint_zone,
            model_carbon_footprint_total_params=model_carbon_footprint_total_params,
            model_carbon_footprint_active_params=model_carbon_footprint_active_params,
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

    def _format_request(
        self,
        json: dict | None = None,
        files: dict | None = None,
        data: dict | None = None,
        endpoint: str | None = None,
    ) -> tuple[str, dict[str, str], dict | None, dict | None, dict | None]:
        """
        Format a request to a client model. Overridden base class method to support TEI Reranking.

        Args:
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.
            endpoint(str): The endpoint to use for the request.

        Returns:
            tuple: The formatted request composed of the url, json, files and data.
        """
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[endpoint].lstrip("/"))
        if json and "model" in json:
            json["model"] = self.name

        if data and "model" in data:
            data["model"] = self.name

        if endpoint.endswith(ENDPOINT__RERANK):
            json = {"query": json["prompt"], "texts": json["input"]}

        return url, json, files, data

    def _format_response(
        self,
        json: dict,
        response: httpx.Response,
        endpoint: str,
        additional_data: dict[str, Any] | None = None,
        request_latency: float = 0.0,
    ) -> httpx.Response:
        """
        Format a response from a client model and add usage data and model ID to the response. This method can be overridden by a subclass to add additional headers or parameters.

        Args:
            json(dict): The JSON body of the request to the API.
            response(httpx.Response): The response from the API.
            additional_data(Dict[str, Any]): The additional data to add to the response (default: {}).

        Returns:
            httpx.Response: The formatted response.
        """

        if additional_data is None:
            additional_data = {}

        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            data = response.json()
            if isinstance(data, list):  # for TEI reranking
                data = {"data": data}
            data.update(self._get_additional_data(json=json, data=data, stream=False, endpoint=endpoint, request_latency=request_latency))
            data.update(additional_data)
            response = httpx.Response(status_code=response.status_code, content=dumps(data))

        return response
