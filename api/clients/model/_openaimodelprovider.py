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


class OpenaiModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: "/v1/audio/transcriptions",
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__EMBEDDINGS: "/v1/embeddings",
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__OCR: "/v1/chat/completions",
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
        Initialize the OpenAI model provider and check if the model is available.
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
