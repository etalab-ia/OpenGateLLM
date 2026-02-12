import base64
from enum import Enum
from typing import Literal

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from mistralai.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage
from pydantic import Field, ValidationError, field_validator

from api.schemas import BaseModel
from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import RequestContent
from api.schemas.usage import Usage
from api.utils.exceptions import FileSizeLimitExceededException
from api.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
SUPPORTED_LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))}
SUPPORTED_LANGUAGES["EMPTY"] = ""

AudioTranscriptionLanguage = Enum("AudioTranscriptionLanguage", SUPPORTED_LANGUAGES, type=str)


class CreateAudioTranscription(BaseModel):
    file: UploadFile
    model: str
    language: AudioTranscriptionLanguage
    prompt: str
    response_format: Literal["json", "text"]
    temperature: float

    # fmt: off
    @classmethod
    def as_form(
        cls,
        file: UploadFile = File(default=..., description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
        model: str = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported."),
        language: AudioTranscriptionLanguage = Form(default=AudioTranscriptionLanguage.EMPTY, description="The language of the output audio. If the output language is different than the audio language, the audio language will be translated into the output language. Supplying the output language in ISO-639-1 (e.g. en, fr) format will improve accuracy and latency."),
        prompt: str = Form(default="", description="An optional text to tell the model what to do with the input audio."),
        response_format: Literal["json", "text"] = Form(default="json", description="The format of the transcript output, in one of these formats: `json` or `text`."),
        temperature: float = Form(default=0.0, ge=0.0, le=1.0, description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit."),
    ) -> "CreateAudioTranscription":
        try:
            return cls(
                file=file,
                model=model,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
            )
        except ValidationError as exc:
            raise RequestValidationError(exc.errors())

    @field_validator("file", mode="after")
    @classmethod
    def validate_file(cls, file: UploadFile) -> UploadFile:
        if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
            raise FileSizeLimitExceededException()
        return file

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
                request_content.form["language"] = "en" if request_content.form["language"] == "" else request_content.form["language"]

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
