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


class MarkerModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: None,
        ENDPOINT__CHAT_COMPLETIONS: None,
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: "/health",
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
