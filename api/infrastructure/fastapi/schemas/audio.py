from enum import StrEnum
from typing import Annotated

from fastapi import File, Form, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import Field, ValidationError

from api.domain import BaseModel
from api.domain.usage.entities import Usage
from api.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
AudioTranscriptionLanguage = StrEnum("AudioTranscriptionLanguage", {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))})


class AudioTranscriptionsResponseFormat(StrEnum):
    JSON = "json"
    TEXT = "text"
    VERBOSE_JSON = "verbose_json"
    DIARIZED_JSON = "diarized_json"
    SRT = "srt"
    VTT = "vtt"


PLAIN_TEXT_SUBTITLE_FORMATS = {
    AudioTranscriptionsResponseFormat.TEXT: "text/plain",
    AudioTranscriptionsResponseFormat.SRT: "application/x-subrip",
    AudioTranscriptionsResponseFormat.VTT: "text/vtt",
}


class Segment(BaseModel):
    id: Annotated[int, Field(default=..., description="A unique identifier for the segment.")] = Field(default=..., description="A unique identifier for the segment.")  # fmt: off
    type: Annotated[str, Field(default="transcript.text.segment", description="The type of the segment.")] = Field(default="transcript.text.segment", description="The type of the segment.")  # fmt: off
    text: Annotated[str, Field(default=..., description="The segment text.")] = Field(default=..., description="The segment text.")
    start: Annotated[float, Field(default=..., description="Start time of the segment in seconds.")] = Field(default=..., description="Start time of the segment in seconds.")  # fmt: off
    end: Annotated[float, Field(default=..., description="End time of the segment in seconds.")] = Field(default=..., description="End time of the segment in seconds.")  # fmt: off
    speaker: Annotated[str | None, Field(default=None, description="Speaker label assigned by diarization, if available.")] = Field(default=None, description="Speaker label assigned by diarization, if available.")  # fmt: off


class AudioTranscriptionsResponse(BaseModel):
    id: Annotated[str, Field(default=..., description="A unique identifier for the audio transcription.")] = Field(default=..., description="A unique identifier for the audio transcription.")  # fmt: off
    text: Annotated[str, Field(default=..., description="The transcription text.")] = Field(default=..., description="The transcription text.")
    model: Annotated[str, Field(default=..., description="The model used to generate the transcription.")] = Field(default=..., description="The model used to generate the transcription.")  # fmt: off
    segments: Annotated[list[Segment] | None, Field(default=None, description="Diarized segments, only set when `response_format=diarized_json`.")] = Field(default=None, description="Diarized segments, only set when `response_format=diarized_json`.")  # fmt: off
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")] = Field(default_factory=Usage, description="Usage information for the request.")  # fmt: off


class CreateAudioTranscriptionsForm(BaseModel):
    file: UploadFile
    model: str
    language: AudioTranscriptionLanguage | None
    prompt: str
    response_format: AudioTranscriptionsResponseFormat
    temperature: float

    # fmt: off
    @classmethod
    def as_form(
        cls,
        file: UploadFile = File(default=..., description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
        model: str = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported."),
        language: AudioTranscriptionLanguage | None = Form(default=None, description="The language of the output audio. If the output language is different than the audio language, the audio language will be translated into the output language. Output language must be supplied in ISO-639-1 format (e.g. en, fr) format."),
        prompt: str = Form(default="", description="An optional text to tell the model what to do with the input audio."),
        response_format: AudioTranscriptionsResponseFormat = Form(default=AudioTranscriptionsResponseFormat.JSON, description="The format of the transcript output: `json` (default), `text`, `diarized_json` to return per-segment speaker labels, `srt` or `vtt` for subtitle formats."),
        temperature: float = Form(default=0.0, ge=0.0, le=1.0, description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit."),
    ) -> "CreateAudioTranscriptionsForm":
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
