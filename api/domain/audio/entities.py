from enum import StrEnum

from fastapi import UploadFile
from pydantic import Field

from api.domain import BaseModel
from api.domain.usage.entities import Usage
from api.utils.variables import SUPPORTED_LANGUAGES

SUPPORTED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys()) + list(SUPPORTED_LANGUAGES.values())
AudioTranscriptionLanguage = StrEnum("AudioTranscriptionLanguage", {str(lang).upper(): str(lang) for lang in sorted(set(SUPPORTED_LANGUAGES))})


class AudioTranscriptionsResponseFormat(StrEnum):
    JSON = ("json", "application/json")
    TEXT = ("text", "text/plain")
    DIARIZED_JSON = ("diarized_json", "application/json")
    SRT = ("srt", "application/x-subrip")
    VERBOSE_JSON = ("verbose_json", "application/json")
    VTT = ("vtt", "text/vtt")

    def __new__(cls, value: str, media_type: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.media_type = media_type

        return obj


class Segment(BaseModel):
    id: int = Field(default=..., description="A unique identifier for the segment.")
    type: str = Field(default="transcript.text.segment", description="The type of the segment.")
    text: str = Field(default=..., description="The segment text.")
    start: float = Field(default=..., description="Start time of the segment in seconds.")
    end: float = Field(default=..., description="End time of the segment in seconds.")
    speaker: str | None = Field(default=None, description="Speaker label assigned by diarization, if available.")


class AudioTranscriptions(BaseModel):
    id: str = Field(default=..., description="A unique identifier for the audio transcription.")
    text: str = Field(default=..., description="The transcription text.")
    model: str = Field(default=..., description="The model used to generate the transcription.")
    segments: list[Segment] | None = Field(default=None, description="Diarized segments, only set when response format is `diarized_json` or `verbose_json`.")  # fmt: off
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")


class CreateAudioTranscriptionsBody(BaseModel):
    file: UploadFile
    model: str
    language: AudioTranscriptionLanguage | None
    prompt: str
    response_format: AudioTranscriptionsResponseFormat
    temperature: float

    def get_prompts(self) -> list[str]:
        return [self.prompt]
