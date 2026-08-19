import base64
from typing import Literal

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage
from pydantic import ValidationError

from api.domain import BaseModel
from api.domain.audio.entities import AudioTranscriptions, AudioTranscriptionsResponseFormat
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
            body = MistralCreateAudioTranscriptionsBody.model_validate(original_request.payload.model_dump(mode="json", exclude={"file"}))
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        text = body.prompt or f"Transcribe this audio in this language : {body.language or 'en'}"  # fmt: off
        file = original_request.payload.file.file
        input_audio = base64.b64encode(file).decode("utf-8")
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
        request_id = self._extract_request_id(original_response=original_response)
        if original_request.payload.response_format == AudioTranscriptionsResponseFormat.TEXT:
            return ProviderFormattedResponse(id=request_id, text=text)

        data = AudioTranscriptions(id=request_id, text=text, model=original_request.payload.model)
        return ProviderFormattedResponse(id=request_id, data=data)
