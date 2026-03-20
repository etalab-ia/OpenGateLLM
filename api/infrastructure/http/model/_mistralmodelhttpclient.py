import base64
from http import HTTPMethod

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat

from ._modelhttpclient import FormattedModelRequest, FormattedModelResponse, ModelHttpClient, ModelHttpClientEndpoints, ModelHttpExchange


class MistralModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(audio_transcriptions=(HTTPMethod.POST, "/v1/chat/completions"), rerank=None)
    TYPE = ProviderType.MISTRAL

    # request formatting
    def format_chat_completion_request(self, exchange: ModelHttpExchange) -> ModelHttpExchange:
        # @TODO: build body with model_fields_set to exclude unset fields

        # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
        body = {
            "frequency_penalty": exchange.original_request.body.get("frequency_penalty") or 0.0,
            "max_tokens": exchange.original_request.body.get("max_tokens"),
            "messages": exchange.original_request.body.get("messages"),
            "model": self.model_name,
            "n": exchange.original_request.body.get("n"),
            "parallel_tool_calls": exchange.original_request.body.get("parallel_tool_calls") or False,
            "prediction": exchange.original_request.body.get("prediction") or {},
            "presence_penalty": exchange.original_request.body.get("presence_penalty") or 0.0,
            "prompt_mode": exchange.original_request.body.get("prompt_mode"),
            "random_seed": exchange.original_request.body.get("random_seed") or exchange.original_request.body.get("seed"),
            "response_format": exchange.original_request.body.get("response_format") or {"type": "text"},
            "safe_prompt": exchange.original_request.body.get("safe_prompt") or False,
            "stop": exchange.original_request.body.get("stop") or [],
            "stream": exchange.original_request.body.get("stream") or False,
            "temperature": exchange.original_request.body.get("temperature"),
            "tool_choice": exchange.original_request.body.get("tool_choice"),
            "tools": exchange.original_request.body.get("tools"),
            "top_p": exchange.original_request.body.get("top_p") or 1.0,
        }

        exchange.formatted_request = FormattedModelRequest(
            method=self.ENDPOINT_TABLE.chat_completions[0],
            endpoint=self.ENDPOINT_TABLE.chat_completions[1],
            body=body,
        )

        return exchange

    def format_audio_transcription_request(self, exchange: ModelHttpExchange) -> ModelHttpExchange:
        text = exchange.original_request.form.get("prompt") or f"Transcribe this audio in this language : {exchange.original_request.form.get('language', 'en')}"  # fmt: off
        input_audio = base64.b64encode(exchange.original_request.files["file"][1]).decode("utf-8")
        exchange.formatted_request = FormattedModelRequest(
            method=self.ENDPOINT_TABLE.audio_transcriptions[0],
            endpoint=self.ENDPOINT_TABLE.audio_transcriptions[1],
            body=ChatCompletionRequest(
                model=self.model_name,
                messages=[
                    UserMessage(
                        role="user",
                        content=[AudioChunk(type="input_audio", input_audio=input_audio), TextChunk(type="text", text=text)],
                    )
                ],
                temperature=exchange.original_request.form.get("temperature"),
            ).model_dump(),
        )

        return exchange

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
