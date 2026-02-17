import logging
from urllib.parse import urljoin

import httpx

from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import ProviderEndpoints
from api.utils.variables import EndpointRoute

from ._basemodelprovider import BaseModelProvider

logger = logging.getLogger(__name__)


class TeiModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = ProviderEndpoints(
        audio_transcriptions=None,
        chat_completions=None,
        embeddings="/v1/embeddings",
        models="/info",
        ocr=None,
        rerank="/rerank",
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
        self.type = ProviderType.TEI

    async def get_max_context_length(self) -> int | None:
        url = urljoin(base=self.url, url=self.ENDPOINT_TABLE.get_endpoint(endpoint=EndpointRoute.MODELS).lstrip("/"))

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Error getting max context length for {self.model_name}: {e}", exc_info=True)
            raise AssertionError(f"Model is not reachable ({e}).")

        data = response.json()
        assert self.model_name == data["model_id"], f"Model not found ({self.model_name})."
        max_context_length = data.get("max_input_length")
        return max_context_length
