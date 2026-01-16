import base64
from enum import Enum

from mistralai.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage
from pydantic import Field

from api.schemas import BaseModel
from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import RequestContent
from api.schemas.usage import Usage
from api.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
SUPPORTED_LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))}
SUPPORTED_LANGUAGES["EMPTY"] = ""

AudioTranscriptionLanguage = Enum("AudioTranscriptionLanguage", SUPPORTED_LANGUAGES, type=str)


class CreateAudioTranscription(BaseModel):
    @staticmethod
    def format_request(provider_type: ProviderType, request_content: RequestContent):
        match provider_type:
            case ProviderType.ALBERT:
                request_content.form["response_format"] = "json"
                return request_content

            case ProviderType.MISTRAL:
                text = request_content.form.get("prompt") or f"Transcribe this audio in this language : {request_content.form.get("language", "en")}"
                input_audio = base64.b64encode(request_content.files["file"][1]).decode("utf-8")
                request_content.json = ChatCompletionRequest(
                    model=request_content.form["model"],
                    messages=[
                        UserMessage(
                            role="user",
                            content=[AudioChunk(type="input_audio", input_audio=input_audio), TextChunk(type="text", text=text)],
                        )
                    ],
                    temperature=request_content.form.get("temperature"),
                ).model_dump()
                request_content.files = {}
                request_content.form = {}
                return request_content

            case ProviderType.VLLM:
                if request_content.form["language"] == AudioTranscriptionLanguage.EMPTY:
                    request_content.form.pop("language")

                if request_content.form.get("temperature") is None:
                    request_content.form.pop("temperature")

                request_content.form["response_format"] = "json"
                return request_content

            case _:
                raise NotImplementedError(f"Provider {provider_type} not implemented")


class AudioTranscription(BaseModel):
    id: str = Field(default=..., description="A unique identifier for the audio transcription.")
    text: str = Field(default=..., description="The transcription text.")
    model: str = Field(default=..., description="The model used to generate the transcription.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")

    @classmethod
    def build_from(cls, provider_type: ProviderType, request_content: RequestContent, response_data: dict) -> "AudioTranscription":
        match provider_type:
            case ProviderType.ALBERT:
                response_data.update(request_content.additional_data)
                return cls(**response_data)

            case ProviderType.MISTRAL:
                text = response_data["choices"][0]["message"]["content"]
                return cls(text=text, **request_content.additional_data)

            case ProviderType.VLLM:
                response_data.update(request_content.additional_data)
                return cls(**response_data)

            case _:
                raise NotImplementedError(f"Provider {provider_type} not implemented")
