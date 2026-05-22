import base64
from contextvars import ContextVar
from typing import Literal

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage
from pydantic import ValidationError

from api.domain import BaseModel
from api.domain.audio.entities import AudioTranscription, AudioTranscriptionResponseFormat
from api.domain.model.entities import Model, Models, ModelType
from api.domain.provider.entities import (
    ProviderFormattedRequest,
    ProviderFormattedResponse,
    ProviderOriginalRequest,
    ProviderOriginalResponse,
)
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.http.adapters import AudioTranscriptionsAdapter, ChatCompletionsAdapter, ModelsAdapter, RerankAdapter
from api.schemas.audio import AudioTranscriptionLanguage


class MistralCreateAudioTranscriptionBody(BaseModel):
    model: str
    language: AudioTranscriptionLanguage | None
    prompt: str
    response_format: Literal["json", "text"]
    temperature: float


class MistralAudioTranscriptionAdapter(AudioTranscriptionsAdapter):
    TARGET_ENDPOINT_ROUTE = "/v1/chat/completions"

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        try:
            body = MistralCreateAudioTranscriptionBody.model_validate(original_request.form)
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        text = original_request.form.prompt or f"Transcribe this audio in this language : {original_request.form.language or 'en'}"  # fmt: off
        input_audio = base64.b64encode(original_request.files["file"][1]).decode("utf-8")
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        return ProviderFormattedRequest(
            method=self.TARGET_ENDPOINT_METHOD,
            url=target_url,
            body=ChatCompletionRequest(
                model=self.provider.model_name,
                messages=[
                    UserMessage(
                        role="user",
                        content=[AudioChunk(type="input_audio", input_audio=input_audio), TextChunk(type="text", text=text)],
                    )
                ],
                temperature=body.temperature,
            ).model_dump(),
        )

    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        request_context: ContextVar[RequestContext],
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        text = original_response.data["choices"][0]["message"]["content"]
        if original_request.form.response_format == AudioTranscriptionResponseFormat.TEXT:
            return ProviderFormattedResponse(text=text, metrics=original_response.metrics)

        formatted_response = ProviderFormattedResponse(data=AudioTranscription(text=text), metrics=original_response.metrics)
        request_id = self._extract_request_id(original_response=original_response)
        request_context.get().id = request_id
        formatted_response.data.id = request_id
        formatted_response.data.model = original_request.form.model

        usage = self._compute_usage(formatted_response=formatted_response, prompt_tokens=prompt_tokens)
        request_context.get().usage = usage
        formatted_response.data.usage = usage

        return formatted_response


class MistralChatCompletionAdapter(ChatCompletionsAdapter):
    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest:
        # @TODO: build body with model_fields_set to exclude unset fields
        # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
        body = {
            "frequency_penalty": original_request.body.frequency_penalty or 0.0,
            "max_tokens": original_request.body.max_tokens,
            "messages": original_request.body.messages,
            "model": self.provider.model_name,
            "n": original_request.body.n,
            "parallel_tool_calls": original_request.body.parallel_tool_calls or False,
            "prediction": original_request.body.prediction or {},
            "presence_penalty": original_request.body.presence_penalty or 0.0,
            "prompt_mode": original_request.body.prompt_mode,
            "random_seed": original_request.body.random_seed or original_request.body.seed,
            "response_format": original_request.body.response_format or {"type": "text"},
            "safe_prompt": original_request.body.safe_prompt or False,
            "stop": original_request.body.stop or [],
            "stream": original_request.body.stream or False,
            "temperature": original_request.body.temperature,
            "tool_choice": original_request.body.tool_choice,
            "tools": original_request.body.tools,
            "top_p": original_request.body.top_p or 1.0,
        }
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)

        return ProviderFormattedRequest(method=self.TARGET_ENDPOINT_METHOD, url=target_url, body=body)


class MistralModelsAdapter(ModelsAdapter):
    def format_response(
        self,
        original_response: ProviderOriginalResponse,
        original_request: ProviderOriginalRequest,
        request_context: ContextVar[RequestContext],
        prompt_tokens: int = 0,
    ) -> ProviderFormattedResponse:
        return ProviderFormattedResponse(
            data=Models(
                data=[
                    Model(
                        id=model["id"],
                        created=model["created"],
                        owned_by=model["owned_by"],
                        max_context_length=model["max_context_length"],
                        type=ModelType.TEXT_GENERATION,  # dummy value, not used
                    )
                    for model in original_response.data.get("data", [])
                ]
            ),
            metrics=original_response.metrics,
        )


class MistralRerankAdapter(RerankAdapter):
    TARGET_ENDPOINT_ROUTE = None
