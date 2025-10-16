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
        model_carbon_footprint_zone: str | None,
        model_carbon_footprint_total_params: int | None,
        model_carbon_footprint_active_params: int | None,
    ) -> None:
        """
        Initialize the vLLM model provider and check if the model is available.
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

        async with httpx.AsyncClient() as client:
            response = await client.get(url=url, headers=self.headers, timeout=self.timeout)
            assert response.status_code == 200, f"Model is not reachable ({response.status_code} - {response.text})."

        data = response.json()
        models = [model for model in data["data"] if model["id"] == self.name]
        assert len(models) == 1, f"Model not found ({self.name})."

        model = models[0]
        max_context_length = model.get("max_model_len")

        return max_context_length
