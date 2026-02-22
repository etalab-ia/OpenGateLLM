# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Mapping, cast
from typing_extensions import Literal

import httpx

from ..types import audio_transcribe_params
from .._types import Body, Omit, Query, Headers, NotGiven, FileTypes, omit, not_given
from .._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import (
    to_raw_response_wrapper,
    to_streamed_response_wrapper,
    async_to_raw_response_wrapper,
    async_to_streamed_response_wrapper,
)
from .._base_client import make_request_options
from ..types.audio_transcribe_response import AudioTranscribeResponse

__all__ = ["AudioResource", "AsyncAudioResource"]


class AudioResource(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AudioResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return AudioResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AudioResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return AudioResourceWithStreamingResponse(self)

    def transcribe(
        self,
        *,
        file: FileTypes,
        model: str,
        language: Literal[
            "af",
            "afrikaans",
            "albanian",
            "am",
            "amharic",
            "ar",
            "arabic",
            "armenian",
            "as",
            "assamese",
            "az",
            "azerbaijani",
            "ba",
            "bashkir",
            "basque",
            "be",
            "belarusian",
            "bengali",
            "bg",
            "bn",
            "bo",
            "bosnian",
            "br",
            "breton",
            "bs",
            "bulgarian",
            "burmese",
            "ca",
            "cantonese",
            "castilian",
            "catalan",
            "chinese",
            "croatian",
            "cs",
            "cy",
            "czech",
            "da",
            "danish",
            "de",
            "dutch",
            "el",
            "en",
            "english",
            "es",
            "estonian",
            "et",
            "eu",
            "fa",
            "faroese",
            "fi",
            "finnish",
            "flemish",
            "fo",
            "fr",
            "french",
            "galician",
            "georgian",
            "german",
            "gl",
            "greek",
            "gu",
            "gujarati",
            "ha",
            "haitian",
            "haitian creole",
            "hausa",
            "haw",
            "hawaiian",
            "he",
            "hebrew",
            "hi",
            "hindi",
            "hr",
            "ht",
            "hu",
            "hungarian",
            "hy",
            "icelandic",
            "id",
            "indonesian",
            "is",
            "it",
            "italian",
            "ja",
            "japanese",
            "javanese",
            "jw",
            "ka",
            "kannada",
            "kazakh",
            "khmer",
            "kk",
            "km",
            "kn",
            "ko",
            "korean",
            "la",
            "lao",
            "latin",
            "latvian",
            "lb",
            "letzeburgesch",
            "lingala",
            "lithuanian",
            "ln",
            "lo",
            "lt",
            "luxembourgish",
            "lv",
            "macedonian",
            "malagasy",
            "malay",
            "malayalam",
            "maltese",
            "mandarin",
            "maori",
            "marathi",
            "mg",
            "mi",
            "mk",
            "ml",
            "mn",
            "moldavian",
            "moldovan",
            "mongolian",
            "mr",
            "ms",
            "mt",
            "my",
            "myanmar",
            "ne",
            "nepali",
            "nl",
            "nn",
            "no",
            "norwegian",
            "nynorsk",
            "oc",
            "occitan",
            "pa",
            "panjabi",
            "pashto",
            "persian",
            "pl",
            "polish",
            "portuguese",
            "ps",
            "pt",
            "punjabi",
            "pushto",
            "ro",
            "romanian",
            "ru",
            "russian",
            "sa",
            "sanskrit",
            "sd",
            "serbian",
            "shona",
            "si",
            "sindhi",
            "sinhala",
            "sinhalese",
            "sk",
            "sl",
            "slovak",
            "slovenian",
            "sn",
            "so",
            "somali",
            "spanish",
            "sq",
            "sr",
            "su",
            "sundanese",
            "sv",
            "sw",
            "swahili",
            "swedish",
            "ta",
            "tagalog",
            "tajik",
            "tamil",
            "tatar",
            "te",
            "telugu",
            "tg",
            "th",
            "thai",
            "tibetan",
            "tk",
            "tl",
            "tr",
            "tt",
            "turkish",
            "turkmen",
            "uk",
            "ukrainian",
            "ur",
            "urdu",
            "uz",
            "uzbek",
            "valencian",
            "vi",
            "vietnamese",
            "welsh",
            "yi",
            "yiddish",
            "yo",
            "yoruba",
            "yue",
            "zh",
            "",
        ]
        | Omit = omit,
        prompt: str | Omit = omit,
        response_format: Literal["json", "text"] | Omit = omit,
        temperature: float | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> AudioTranscribeResponse:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              mp3 or wav.

          model: ID of the model to use. Call `/v1/models` endpoint to get the list of available
              models, only `automatic-speech-recognition` model type is supported.

          language: The language of the output audio. If the output language is different than the
              audio language, the audio language will be translated into the output language.
              Supplying the output language in ISO-639-1 (e.g. en, fr) format will improve
              accuracy and latency.

          prompt: An optional text to tell the model what to do with the input audio.

          response_format: The format of the transcript output, in one of these formats: `json` or `text`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use log probability to automatically
              increase the temperature until certain thresholds are hit.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "language": language,
                "prompt": prompt,
                "response_format": response_format,
                "temperature": temperature,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/v1/audio/transcriptions",
            body=maybe_transform(body, audio_transcribe_params.AudioTranscribeParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=AudioTranscribeResponse,
        )


class AsyncAudioResource(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncAudioResourceWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#accessing-raw-response-data-eg-headers
        """
        return AsyncAudioResourceWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncAudioResourceWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/etalab-ia/OpenGateLLM#with_streaming_response
        """
        return AsyncAudioResourceWithStreamingResponse(self)

    async def transcribe(
        self,
        *,
        file: FileTypes,
        model: str,
        language: Literal[
            "af",
            "afrikaans",
            "albanian",
            "am",
            "amharic",
            "ar",
            "arabic",
            "armenian",
            "as",
            "assamese",
            "az",
            "azerbaijani",
            "ba",
            "bashkir",
            "basque",
            "be",
            "belarusian",
            "bengali",
            "bg",
            "bn",
            "bo",
            "bosnian",
            "br",
            "breton",
            "bs",
            "bulgarian",
            "burmese",
            "ca",
            "cantonese",
            "castilian",
            "catalan",
            "chinese",
            "croatian",
            "cs",
            "cy",
            "czech",
            "da",
            "danish",
            "de",
            "dutch",
            "el",
            "en",
            "english",
            "es",
            "estonian",
            "et",
            "eu",
            "fa",
            "faroese",
            "fi",
            "finnish",
            "flemish",
            "fo",
            "fr",
            "french",
            "galician",
            "georgian",
            "german",
            "gl",
            "greek",
            "gu",
            "gujarati",
            "ha",
            "haitian",
            "haitian creole",
            "hausa",
            "haw",
            "hawaiian",
            "he",
            "hebrew",
            "hi",
            "hindi",
            "hr",
            "ht",
            "hu",
            "hungarian",
            "hy",
            "icelandic",
            "id",
            "indonesian",
            "is",
            "it",
            "italian",
            "ja",
            "japanese",
            "javanese",
            "jw",
            "ka",
            "kannada",
            "kazakh",
            "khmer",
            "kk",
            "km",
            "kn",
            "ko",
            "korean",
            "la",
            "lao",
            "latin",
            "latvian",
            "lb",
            "letzeburgesch",
            "lingala",
            "lithuanian",
            "ln",
            "lo",
            "lt",
            "luxembourgish",
            "lv",
            "macedonian",
            "malagasy",
            "malay",
            "malayalam",
            "maltese",
            "mandarin",
            "maori",
            "marathi",
            "mg",
            "mi",
            "mk",
            "ml",
            "mn",
            "moldavian",
            "moldovan",
            "mongolian",
            "mr",
            "ms",
            "mt",
            "my",
            "myanmar",
            "ne",
            "nepali",
            "nl",
            "nn",
            "no",
            "norwegian",
            "nynorsk",
            "oc",
            "occitan",
            "pa",
            "panjabi",
            "pashto",
            "persian",
            "pl",
            "polish",
            "portuguese",
            "ps",
            "pt",
            "punjabi",
            "pushto",
            "ro",
            "romanian",
            "ru",
            "russian",
            "sa",
            "sanskrit",
            "sd",
            "serbian",
            "shona",
            "si",
            "sindhi",
            "sinhala",
            "sinhalese",
            "sk",
            "sl",
            "slovak",
            "slovenian",
            "sn",
            "so",
            "somali",
            "spanish",
            "sq",
            "sr",
            "su",
            "sundanese",
            "sv",
            "sw",
            "swahili",
            "swedish",
            "ta",
            "tagalog",
            "tajik",
            "tamil",
            "tatar",
            "te",
            "telugu",
            "tg",
            "th",
            "thai",
            "tibetan",
            "tk",
            "tl",
            "tr",
            "tt",
            "turkish",
            "turkmen",
            "uk",
            "ukrainian",
            "ur",
            "urdu",
            "uz",
            "uzbek",
            "valencian",
            "vi",
            "vietnamese",
            "welsh",
            "yi",
            "yiddish",
            "yo",
            "yoruba",
            "yue",
            "zh",
            "",
        ]
        | Omit = omit,
        prompt: str | Omit = omit,
        response_format: Literal["json", "text"] | Omit = omit,
        temperature: float | Omit = omit,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = not_given,
    ) -> AudioTranscribeResponse:
        """
        Transcribes audio into the input language.

        Args:
          file:
              The audio file object (not file name) to transcribe, in one of these formats:
              mp3 or wav.

          model: ID of the model to use. Call `/v1/models` endpoint to get the list of available
              models, only `automatic-speech-recognition` model type is supported.

          language: The language of the output audio. If the output language is different than the
              audio language, the audio language will be translated into the output language.
              Supplying the output language in ISO-639-1 (e.g. en, fr) format will improve
              accuracy and latency.

          prompt: An optional text to tell the model what to do with the input audio.

          response_format: The format of the transcript output, in one of these formats: `json` or `text`.

          temperature: The sampling temperature, between 0 and 1. Higher values like 0.8 will make the
              output more random, while lower values like 0.2 will make it more focused and
              deterministic. If set to 0, the model will use log probability to automatically
              increase the temperature until certain thresholds are hit.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "file": file,
                "model": model,
                "language": language,
                "prompt": prompt,
                "response_format": response_format,
                "temperature": temperature,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["file"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/v1/audio/transcriptions",
            body=await async_maybe_transform(body, audio_transcribe_params.AudioTranscribeParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=AudioTranscribeResponse,
        )


class AudioResourceWithRawResponse:
    def __init__(self, audio: AudioResource) -> None:
        self._audio = audio

        self.transcribe = to_raw_response_wrapper(
            audio.transcribe,
        )


class AsyncAudioResourceWithRawResponse:
    def __init__(self, audio: AsyncAudioResource) -> None:
        self._audio = audio

        self.transcribe = async_to_raw_response_wrapper(
            audio.transcribe,
        )


class AudioResourceWithStreamingResponse:
    def __init__(self, audio: AudioResource) -> None:
        self._audio = audio

        self.transcribe = to_streamed_response_wrapper(
            audio.transcribe,
        )


class AsyncAudioResourceWithStreamingResponse:
    def __init__(self, audio: AsyncAudioResource) -> None:
        self._audio = audio

        self.transcribe = async_to_streamed_response_wrapper(
            audio.transcribe,
        )
