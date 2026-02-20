import logging
from urllib.parse import urljoin

import httpx

from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import ProviderEndpoints
from api.utils.variables import EndpointRoute

from ._basemodelprovider import BaseModelProvider

logger = logging.getLogger(__name__)


class OpenaiModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = ProviderEndpoints(
        audio_transcriptions="/v1/audio/transcriptions",
        chat_completions="/v1/chat/completions",
        embeddings="/v1/embeddings",
        models="/v1/models",
        ocr="/v1/chat/completions",
        rerank=None,
    )

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
        Initialize the OpenAI model provider and check if the model is available.
        """
        super().__init__(
            model_name=model_name,
            model_hosting_zone=model_hosting_zone,
            model_total_params=model_total_params,
            model_active_params=model_active_params,
            url=url,
            key=key,
            timeout=timeout,
        )
        self.type = ProviderType.OPENAI

    async def get_max_context_length(self) -> int | None:
        url = urljoin(base=str(self.url), url=self.ENDPOINT_TABLE.get_endpoint(endpoint=EndpointRoute.MODELS).lstrip("/"))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error getting max context length for {self.model_name}: {e}", exc_info=True)
            raise AssertionError(f"Model is not reachable ({e}).")

        data = response.json()["data"]
        models = [model for model in data if model["id"] == self.model_name]
        assert len(models) == 1, f"Model not found ({self.model_name})."

        model = models[0]
        max_context_length = model.get("max_context_length")

        return max_context_length
