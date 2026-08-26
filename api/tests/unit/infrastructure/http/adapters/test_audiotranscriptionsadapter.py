import base64
from tempfile import SpooledTemporaryFile

from api.domain.audio.entities import AudioTranscriptionsResponseFormat, CreateAudioTranscriptionsFile, CreateAudioTranscriptionsForm
from api.domain.provider.entities import ProviderRawResponse, ProviderRequest, ProviderType
from api.infrastructure.http.adapters.audio import AudioTranscriptionsAdapter
from api.infrastructure.http.adapters.audio.mistral import MistralAudioTranscriptionsAdapter
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute

AUDIO_BYTES = b"audio-bytes"


def mock_audio_file() -> SpooledTemporaryFile:
    file = SpooledTemporaryFile()
    file.write(AUDIO_BYTES)
    file.seek(0)
    return file


def _original_request(**overrides) -> ProviderRequest:
    form = CreateAudioTranscriptionsForm(
        file=CreateAudioTranscriptionsFile(name="speech.mp3", file=mock_audio_file(), content_type="audio/mpeg", size=11),
        model="audio-router",
        language="en",
        prompt="",
        response_format=AudioTranscriptionsResponseFormat.JSON,
        temperature=0.0,
    )
    payload = {
        "endpoint": EndpointRoute.AUDIO_TRANSCRIPTIONS,
        "payload": form,
    }
    payload.update(overrides)
    return ProviderRequest(**payload)


class TestAudioTranscriptionsAdapter:
    def test_should_rewrite_form_model_to_provider_model_name(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="whisper-1")
        adapter = AudioTranscriptionsAdapter(provider=provider)
        original_request = _original_request()

        # Act
        result = adapter.to_http_request(request=original_request)

        # Assert
        assert result.form["model"] == "whisper-1"
        assert original_request.payload.model == "audio-router"
        assert result.files == {"file": ("speech.mp3", original_request.payload.file.file, "audio/mpeg")}
        assert result.body == {}

    def test_should_set_response_model_from_original_form(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="whisper-1")
        adapter = AudioTranscriptionsAdapter(provider=provider)
        original_response = ProviderRawResponse(data={"text": "hello world"})

        # Act
        result = adapter.to_domain_response(request=_original_request(), raw_response=original_response)

        # Assert
        assert result.data.text == "hello world"
        assert result.data.model == "audio-router"


class TestMistralAudioTranscriptionsAdapter:
    def test_should_encode_audio_file_into_chat_completions_body(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test", model_name="voxtral")
        adapter = MistralAudioTranscriptionsAdapter(provider=provider)

        # Act
        result = adapter.to_http_request(request=_original_request())

        # Assert
        assert result.url == "https://mistral.test/v1/chat/completions"
        assert result.body["model"] == "voxtral"
        assert result.body["messages"][0]["content"] == [
            {"type": "input_audio", "input_audio": base64.b64encode(AUDIO_BYTES).decode("utf-8")},
            {"type": "text", "text": "Transcribe this audio in this language : en"},
        ]
        assert result.files == {}
        assert result.form == {}
