import logging
from urllib.parse import urljoin

import httpx

from api.schemas.admin.providers import ProviderType
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


class VllmModelProvider(BaseModelProvider):
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
        model_hosting_zone: str | None,
        model_total_params: int | None,
        model_active_params: int | None,
    ) -> None:
        """
        Initialize the vLLM model provider and check if the model is available.
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
        self.type = ProviderType.VLLM

    async def get_max_context_length(self) -> int | None:
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE[ENDPOINT__MODELS].lstrip("/"))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error getting max context length for {self.model_name}: {e}", exc_info=True)
            raise AssertionError(f"Model is not reachable ({e}).")

        data = response.json()
        models = [model for model in data["data"] if model["id"] == self.model_name]
        assert len(models) == 1, f"Model not found ({self.model_name})."

        model = models[0]
        max_context_length = model.get("max_model_len")

        return max_context_length
