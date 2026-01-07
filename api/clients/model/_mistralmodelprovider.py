import base64
from json import dumps
import logging
from urllib.parse import urljoin

import httpx

from api.schemas.core.models import RequestContent
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


class MistralModelProvider(BaseModelProvider):
    ENDPOINT_TABLE = {
        ENDPOINT__AUDIO_TRANSCRIPTIONS: "/v1/chat/completions",
        ENDPOINT__CHAT_COMPLETIONS: "/v1/chat/completions",
        ENDPOINT__EMBEDDINGS: None,
        ENDPOINT__MODELS: "/v1/models",
        ENDPOINT__OCR: "/v1/ocr",
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
        Initialize the Mistral model provider and check if the model is available.
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
        self._audio_response_format = "json"

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

    def _format_request(self, request_content: RequestContent) -> RequestContent:
        """
        Converts an openAI compatible /chat/completions request to Mistral compatible /chat/completions
        Converts an openAI compatible /audio/transcription request to a Mistral compatible /chat/completions request
        """

        if "model" in request_content.json:
            request_content.json["model"] = self.name

        if "model" in request_content.form:
            request_content.form["model"] = self.name

        if request_content.endpoint == ENDPOINT__CHAT_COMPLETIONS:
            # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
            request_content.json["frequency_penalty"] = 0.0 if request_content.json["frequency_penalty"] is None else request_content.json["frequency_penalty"]  # fmt: off
            request_content.json["random_seed"] = request_content.json.get("random_seed", request_content.json.get("seed"))
            request_content.json["parallel_tool_calls"] = False if request_content.json["parallel_tool_calls"] is None else request_content.json["parallel_tool_calls"]  # fmt: off
            request_content.json["presence_penalty"] = 0.0 if request_content.json["presence_penalty"] is None else request_content.json["presence_penalty"]  # fmt: off
            request_content.json["response_format"] = {"type": "text"} if request_content.json["response_format"] is None else request_content.json["response_format"]  # fmt: off
            if request_content.json.get("stop") is None:
                request_content.json.pop("stop", None)
            request_content.json["stream"] = False if request_content.json["stream"] is None else request_content.json["stream"]
            request_content.json["top_p"] = 1.0 if request_content.json["top_p"] is None else request_content.json["top_p"]

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
            for key in list(request_content.json.keys()):
                if key not in authorized_keys:
                    del request_content.json[key]

        elif request_content.endpoint == ENDPOINT__AUDIO_TRANSCRIPTIONS:
            self._audio_response_format = request_content.json.get("response_format", "json")

            request_content.json = {
                "model": self.name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_audio",
                                "input_audio": base64.b64encode(request_content.files["file"][1]).decode("utf-8"),
                            },
                            {
                                "type": "text",
                                "text": request_content.form.get("prompt")
                                or f"Transcribe this audio in this language : {request_content.form.get("language", "en")}",
                            },
                        ],
                    }
                ],
            }
            if request_content.form.get("temperature"):
                request_content.json["temperature"] = request_content.form["temperature"]

            request_content.files = {}
            request_content.form = {}

        return request_content

    def _format_response(
        self,
        request_content: RequestContent,
        response: httpx.Response,
        request_latency: float = 0.0,
    ) -> httpx.Response:
        content_type = response.headers.get("Content-Type", "")
        if content_type == "application/json":
            response_data = response.json()
            usage = self._get_usage(request_content=request_content, response_data=response_data, stream=False, request_latency=request_latency)

            if request_context.get().id is None:
                request_id = response_data.get("id", generate_request_id())
                request_context.get().id = request_id
            else:
                request_id = request_context.get().id

            additional_data = request_content.additional_data
            additional_data.update({"model": self.name, "id": request_id, "usage": usage.model_dump()})

            if request_content.endpoint == ENDPOINT__AUDIO_TRANSCRIPTIONS:
                transcription_text = response_data["choices"][0]["message"]["content"]

                if self._audio_response_format == "text":
                    response = httpx.Response(status_code=response.status_code, content=transcription_text)
                    return response
                else:
                    # @TODO: add model name
                    additional_data = {"id": response_data.get("id"), "text": transcription_text, "usage": response_data.get("usage")}

            response = httpx.Response(status_code=response.status_code, content=dumps(additional_data))

        return response
