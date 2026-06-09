import base64
from typing import Literal

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage
from pydantic import ValidationError

from api.domain import BaseModel
from api.domain.audio.entities import AudioTranscription, AudioTranscriptionResponseFormat
from api.domain.provider.entities import ProviderFormattedRequest, ProviderFormattedResponse, ProviderOriginalRequest, ProviderOriginalResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.infrastructure.http.adapters.audio import AudioTranscriptionsAdapter
from api.schemas.audio import AudioTranscriptionLanguage


class MistralCreateAudioTranscriptionsBody(BaseModel):
    model: str
    language: AudioTranscriptionLanguage | None
    prompt: str
    response_format: Literal["json", "text"]
    temperature: float


class MistralAudioTranscriptionsAdapter(AudioTranscriptionsAdapter):
    TARGET_ENDPOINT_ROUTE = "/v1/chat/completions"

    def format_request(self, original_request: ProviderOriginalRequest) -> ProviderFormattedRequest | ProviderAdapterValidationRequestError:
        try:
            body = MistralCreateAudioTranscriptionsBody.model_validate(original_request.form)
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
    ) -> ProviderFormattedResponse:
        text = original_response.data["choices"][0]["message"]["content"]
        if original_request.form.response_format == AudioTranscriptionResponseFormat.TEXT:
            return ProviderFormattedResponse(text=text)

        formatted_response = ProviderFormattedResponse(data=AudioTranscription(text=text))
        request_id = self._extract_request_id(original_response=original_response)
        formatted_response.data.id = request_id
        formatted_response.data.model = original_request.form.model

        return formatted_response
