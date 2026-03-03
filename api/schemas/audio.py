<<<<<<< HEAD
import base64
=======
>>>>>>> 8582c6f3 (feat(models): convert get capabilities of a provider with standard forward request method)
from enum import StrEnum

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import Field, ValidationError, field_validator

from api.schemas import BaseModel
from api.schemas.usage import Usage
from api.utils.exceptions import FileSizeLimitExceededException
from api.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
AudioTranscriptionLanguage = StrEnum("AudioTranscriptionLanguage", {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))})


class AudioTranscriptionResponseFormat(StrEnum):
    JSON = "json"
    TEXT = "text"
    VERBOSE_JSON = "verbose_json"


class CreateAudioTranscription(BaseModel):
    file: UploadFile
    model: str
    language: AudioTranscriptionLanguage
    prompt: str
    response_format: AudioTranscriptionResponseFormat
    temperature: float

    # fmt: off
    @classmethod
    def as_form(
        cls,
        file: UploadFile = File(default=..., description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
        model: str = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported."),
        language: AudioTranscriptionLanguage = Form(default=AudioTranscriptionLanguage.ENGLISH, description="The language of the output audio. If the output language is different than the audio language, the audio language will be translated into the output language. Supplying the output language in ISO-639-1 (e.g. en, fr) format will improve accuracy and latency."),
        prompt: str = Form(default="", description="An optional text to tell the model what to do with the input audio."),
        response_format: AudioTranscriptionResponseFormat = Form(default=AudioTranscriptionResponseFormat.JSON, description="The format of the transcript output, in one of these formats: `json` or `text`."),
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


class AudioTranscription(BaseModel):
    id: str = Field(default=..., description="A unique identifier for the audio transcription.")
    text: str = Field(default=..., description="The transcription text.")
    model: str = Field(default=..., description="The model used to generate the transcription.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")
