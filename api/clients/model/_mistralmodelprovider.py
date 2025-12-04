import logging
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


class MistralModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__OCR: None,
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
        Initialize the Mistral model provider and check if the model is available.
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

    async def get_max_context_length(self) -> int | None:
        url = urljoin(base=str(self.url), url=self.ENDPOINT_TABLE[ENDPOINT__MODELS].lstrip("/"))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error getting max context length for {self.name}: {e}", exc_info=True)
            raise AssertionError(f"Model is not reachable ({e}).")

        data = response.json()["data"]
        models = [model for model in data if model["id"] == self.name]
        assert len(models) == 1, f"Model not found ({self.name})."

        model = models[0]
        max_context_length = model.get("max_context_length")

        return max_context_length

    def _format_request(
        self,
        json: dict | None = None,
        files: dict | None = None,
        data: dict | None = None,
        endpoint: str | None = None,
    ) -> tuple[str, dict[str, str] | None, dict | None, dict | None, dict | None]:
        """
        Format a request to a provider model. This method can be overridden by a subclass to add additional headers or parameters. This method format the requested endpoint thanks the ENDPOINT_TABLE attribute.

        Args:
            json(dict): The JSON body to use for the request.
            files(dict): The files to use for the request.
            data(dict): The data to use for the request.
            endpoint(str): The endpoint to use for the request.

        Returns:
            tuple: The formatted request composed of the url, headers, json, files and data.
        """
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[endpoint].lstrip("/"))
        if json and "model" in json:
            json["model"] = self.name

        if data and "model" in data:
            data["model"] = self.name

        if endpoint == ENDPOINT__CHAT_COMPLETIONS:
            # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
            json["frequency_penalty"] = 0.0 if json["frequency_penalty"] is None else json["frequency_penalty"]
            json["random_seed"] = json.get("random_seed", json.get("seed"))
            json["parallel_tool_calls"] = False if json["parallel_tool_calls"] is None else json["parallel_tool_calls"]
            json["presence_penalty"] = 0.0 if json["presence_penalty"] is None else json["presence_penalty"]
            json["response_format"] = {"type": "text"} if json["response_format"] is None else json["response_format"]
            if json.get("stop") is None:
                json.pop("stop", None)
            json["stream"] = False if json["stream"] is None else json["stream"]
            json["top_p"] = 1.0 if json["top_p"] is None else json["top_p"]

            authorized_keys = [
                "frequency_penalty",
                "max_tokens",
                "messages",
                "model",
                "n",
                "parallel_tool_calls",
                "prediction",
                "presence_penalty",
                "prompt_mode",
                "random_seed",
                "response_format",
                "safe_prompt",
                "stop",
                "stream",
                "temperature",
                "tool_choice",
                "tools",
                "top_p",
            ]
            for key in list(json.keys()):
                if key not in authorized_keys:
                    del json[key]

        return url, json, files, data
