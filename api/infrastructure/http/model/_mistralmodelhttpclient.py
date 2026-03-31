import base64
from http import HTTPMethod

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat

from ._modelhttpclient import (
    FormattedModelRequest,
    FormattedModelResponse,
    ModelHttpClient,
    ModelHttpClientEndpoints,
    ModelHttpExchange,
    OriginalModelRequest,
)


class MistralModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(audio_transcriptions=(HTTPMethod.POST, "/v1/chat/completions"), rerank=(None, None))
    TYPE = ProviderType.MISTRAL

    # request formatting
    def get_formatted_chat_completion_request(self, original_request: OriginalModelRequest, method: HTTPMethod, url: str) -> FormattedModelRequest:
        # @TODO: build body with model_fields_set to exclude unset fields

        # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
        body = {
            "frequency_penalty": original_request.body.get("frequency_penalty") or 0.0,
            "max_tokens": original_request.body.get("max_tokens"),
            "messages": original_request.body.get("messages"),
            "model": self.model_name,
            "n": original_request.body.get("n"),
            "parallel_tool_calls": original_request.body.get("parallel_tool_calls") or False,
            "prediction": original_request.body.get("prediction") or {},
            "presence_penalty": original_request.body.get("presence_penalty") or 0.0,
            "prompt_mode": original_request.body.get("prompt_mode"),
            "random_seed": original_request.body.get("random_seed") or original_request.body.get("seed"),
            "response_format": original_request.body.get("response_format") or {"type": "text"},
            "safe_prompt": original_request.body.get("safe_prompt") or False,
            "stop": original_request.body.get("stop") or [],
            "stream": original_request.body.get("stream") or False,
            "temperature": original_request.body.get("temperature"),
            "tool_choice": original_request.body.get("tool_choice"),
            "tools": original_request.body.get("tools"),
            "top_p": original_request.body.get("top_p") or 1.0,
        }

        formatted_request = FormattedModelRequest(method=method, url=url, body=body)

        return formatted_request

    def get_formatted_audio_transcription_request(
        self, original_request: OriginalModelRequest, method: HTTPMethod, url: str
    ) -> FormattedModelRequest:
        text = original_request.form.get("prompt") or f"Transcribe this audio in this language : {original_request.form.get('language', 'en')}"  # fmt: off
        input_audio = base64.b64encode(original_request.files["file"][1]).decode("utf-8")
        formatted_request = FormattedModelRequest(
            method=method,
            url=url,
            body=ChatCompletionRequest(
                model=self.model_name,
                messages=[
                    UserMessage(
                        role="user",
                        content=[AudioChunk(type="input_audio", input_audio=input_audio), TextChunk(type="text", text=text)],
                    )
                ],
                temperature=original_request.form.get("temperature"),
            ).model_dump(),
        )

        return formatted_request

    # response formatting
    def format_response_to_audio_transcription_response(self, exchange: ModelHttpExchange) -> ModelHttpExchange:
        request_id = self._get_request_id(exchange=exchange)
        text = exchange.original_response.data["choices"][0]["message"]["content"]

        if exchange.original_request.form["response_format"] == AudioTranscriptionResponseFormat.TEXT:
            exchange.formatted_response = FormattedModelResponse(text=text)
            return exchange

        usage = self._get_usage(exchange=exchange)
        if usage is not None:
            usage = usage.model_dump()

        exchange.formatted_response = FormattedModelResponse(
            data=AudioTranscription(
                id=request_id,
                model=exchange.original_request.form["model"],
                text=text,
                usage=usage,
            ),
        )
        return exchange

    def format_response_to_models_response(self, exchange: ModelHttpExchange) -> ModelHttpExchange:
        exchange.formatted_response = FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    ModelResponse(
                        id=model["id"],
                        created=model["created"],
                        owned_by=model["owned_by"],
                        max_context_length=model["max_context_length"],
                        aliases=model.get("aliases", []),
                    )
                    for model in exchange.original_response.data.get("data", [])
                ]
            )
        )

        return exchange
