from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from api.domain import BaseModel, ForwardablePayload
from api.domain.model.entities import ProviderJsonResponse
from api.domain.usage.entities import Usage

# Supported language from https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/tokenization_whisper.py
_SUPPORTED_LANGUAGES = {
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "arabic": "ar",
    "armenian": "hy",
    "assamese": "as",
    "azerbaijani": "az",
    "bashkir": "ba",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bosnian": "bs",
    "breton": "br",
    "bulgarian": "bg",
    "burmese": "my",
    "cantonese": "yue",
    "castilian": "es",
    "catalan": "ca",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "faroese": "fo",
    "finnish": "fi",
    "flemish": "nl",
    "french": "fr",
    "galician": "gl",
    "georgian": "ka",
    "german": "de",
    "greek": "el",
    "gujarati": "gu",
    "haitian": "ht",
    "haitian creole": "ht",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "he",
    "hindi": "hi",
    "hungarian": "hu",
    "icelandic": "is",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "kannada": "kn",
    "kazakh": "kk",
    "khmer": "km",
    "korean": "ko",
    "lao": "lo",
    "latin": "la",
    "latvian": "lv",
    "letzeburgesch": "lb",
    "lingala": "ln",
    "lithuanian": "lt",
    "luxembourgish": "lb",
    "macedonian": "mk",
    "malagasy": "mg",
    "malay": "ms",
    "malayalam": "ml",
    "maltese": "mt",
    "mandarin": "zh",
    "maori": "mi",
    "marathi": "mr",
    "moldavian": "ro",
    "moldovan": "ro",
    "mongolian": "mn",
    "myanmar": "my",
    "nepali": "ne",
    "norwegian": "no",
    "nynorsk": "nn",
    "occitan": "oc",
    "panjabi": "pa",
    "pashto": "ps",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "punjabi": "pa",
    "pushto": "ps",
    "romanian": "ro",
    "russian": "ru",
    "sanskrit": "sa",
    "serbian": "sr",
    "shona": "sn",
    "sindhi": "sd",
    "sinhala": "si",
    "sinhalese": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "spanish": "es",
    "sundanese": "su",
    "swahili": "sw",
    "swedish": "sv",
    "tagalog": "tl",
    "tajik": "tg",
    "tamil": "ta",
    "tatar": "tt",
    "telugu": "te",
    "thai": "th",
    "tibetan": "bo",
    "turkish": "tr",
    "turkmen": "tk",
    "ukrainian": "uk",
    "urdu": "ur",
    "uzbek": "uz",
    "valencian": "ca",
    "vietnamese": "vi",
    "welsh": "cy",
    "yiddish": "yi",
    "yoruba": "yo",
}

_SUPPORTED_LANGUAGE_NAMES_AND_CODES = list(_SUPPORTED_LANGUAGES.keys()) + list(_SUPPORTED_LANGUAGES.values())
AudioTranscriptionLanguage = StrEnum(
    "AudioTranscriptionLanguage", {str(lang).upper(): str(lang) for lang in sorted(set(_SUPPORTED_LANGUAGE_NAMES_AND_CODES))}
)


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
    id: Annotated[int, Field(default=..., description="A unique identifier for the segment.")]
    type: Annotated[str, Field(default="transcript.text.segment", description="The type of the segment.")]
    text: Annotated[str, Field(default=..., description="The segment text.")]
    start: Annotated[float, Field(default=..., description="Start time of the segment in seconds.")]
    end: Annotated[float, Field(default=..., description="End time of the segment in seconds.")]
    speaker: Annotated[str | None, Field(default=None, description="Speaker label assigned by diarization, if available.")]


class AudioTranscriptions(ProviderJsonResponse):
    id: str
    model: str
    text: str
    usage: Annotated[Usage, Field(default_factory=Usage)]

    def get_completions(self) -> list[str]:
        return [self.text]


class CreateAudioTranscriptionsFile(BaseModel):
    name: str
    file: Any
    content_type: str
    size: int


class CreateAudioTranscriptionsForm(ForwardablePayload):
    file: CreateAudioTranscriptionsFile
    model: str
    language: AudioTranscriptionLanguage | None
    prompt: str
    response_format: AudioTranscriptionsResponseFormat
    temperature: float

    def get_prompts(self) -> list[str]:
        return [self.prompt]

    def get_files(self) -> dict:
        return {"file": (self.file.name, self.file.file, self.file.content_type)}
