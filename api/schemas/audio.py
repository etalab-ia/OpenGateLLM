from enum import Enum
from typing import Literal

from fastapi import Form
from pydantic import Field

from api.schemas import BaseModel
from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import RequestContent
from api.schemas.usage import Usage
from api.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
SUPPORTED_LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))}

AudioTranscriptionLanguage = Enum("AudioTranscriptionLanguage", SUPPORTED_LANGUAGES, type=str)

AudioTranscriptionModelForm: str = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported.")  # fmt: off
AudioTranscriptionLanguageForm: AudioTranscriptionLanguage | Literal[""] = Form(default="", description="The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency.")  # fmt: off
AudioTranscriptionPromptForm: str | None = Form(default=None, description="An optional text to tell the model what to do with the input audio. Default is `Transcribe this audio in this language : {language}`")  # fmt: off
AudioTranscriptionResponseFormatForm: Literal["json", "text"] = Form(default="json", description="The format of the transcript output, in one of these formats: `json` or `text`.")  # fmt: off
AudioTranscriptionTemperatureForm: float = Form(default=0, ge=0, le=1, description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.")  # fmt: off


class CreateAudioTranscription(BaseModel):
    model: str = AudioTranscriptionModelForm
    language: AudioTranscriptionLanguage | Literal[""] = AudioTranscriptionLanguageForm
    prompt: str = AudioTranscriptionPromptForm
    response_format: Literal["json", "text"] = AudioTranscriptionResponseFormatForm
    temperature: float = AudioTranscriptionTemperatureForm


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
