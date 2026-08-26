import base64
from typing import Literal

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage
from pydantic import ValidationError

from api.domain import BaseModel
from api.domain.audio.entities import AudioTranscriptions, AudioTranscriptionsResponseFormat
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderResponse
from api.domain.provider.errors import ProviderAdapterValidationRequestError
from api.infrastructure.http._httpproviderrequest import HttpProviderRequest
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

    def to_http_request(self, request: ProviderRequest) -> HttpProviderRequest | ProviderAdapterValidationRequestError:
        try:
            body = MistralCreateAudioTranscriptionsBody.model_validate(request.payload.model_dump(mode="json", exclude={"file"}))
        except ValidationError as e:
            return ProviderAdapterValidationRequestError(provider_type=self.provider.type, errors=e.errors())

        text = body.prompt or f"Transcribe this audio in this language : {body.language or 'en'}"  # fmt: off
        file = request.payload.file.file.read()
        input_audio = base64.b64encode(file).decode("utf-8")
        target_url = self._build_target_url(base_url=self.provider.url, target_endpoint_route=self.TARGET_ENDPOINT_ROUTE)
        return HttpProviderRequest(
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

    def to_domain_response(
        self,
        raw_response: ProviderRawResponse,
        request: ProviderRequest,
    ) -> ProviderResponse:
        text = raw_response.data["choices"][0]["message"]["content"]
        request_id = self._extract_request_id(raw_response=raw_response)
        if request.payload.response_format == AudioTranscriptionsResponseFormat.TEXT:
            return ProviderResponse(id=request_id, text=text)

        data = AudioTranscriptions(id=request_id, text=text, model=request.payload.model)
        return ProviderResponse(id=request_id, data=data)
