from api.domain.audio.entities import AudioTranscriptionsResponseFormat, CreateAudioTranscriptionsFile, CreateAudioTranscriptionsForm
from api.domain.provider.entities import ProviderOriginalRequest, ProviderOriginalResponse, ProviderType
from api.infrastructure.http.adapters.audio import AudioTranscriptionsAdapter
from api.infrastructure.http.adapters.audio.mistral import MistralAudioTranscriptionsAdapter
from api.tests.unit.use_case.factories import ProviderFactory
from api.utils.variables import EndpointRoute


def _original_request(**overrides) -> ProviderOriginalRequest:
    form = CreateAudioTranscriptionsForm(
        file=CreateAudioTranscriptionsFile(name="speech.mp3", file=b"audio-bytes", content_type="audio/mpeg", size=11),
        model="audio-router",
        language="en",
        prompt="",
        response_format=AudioTranscriptionsResponseFormat.JSON,
        temperature=0.0,
    )
    payload = {
        "endpoint": EndpointRoute.AUDIO_TRANSCRIPTIONS,
        "payload": form,
        "files": form.get_files(),
    }
    payload.update(overrides)
    return ProviderOriginalRequest(**payload)


class TestAudioTranscriptionsAdapter:
    def test_should_rewrite_form_model_to_provider_model_name(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="whisper-1")
        adapter = AudioTranscriptionsAdapter(provider=provider)
        original_request = _original_request()

        # Act
        result = adapter.format_request(original_request=original_request)

        # Assert
        assert result.form["model"] == "whisper-1"
        assert original_request.payload.model == "audio-router"
        assert result.files == {"file": ("speech.mp3", b"audio-bytes", "audio/mpeg")}
        assert result.body == {}

    def test_should_set_response_model_from_original_form(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.VLLM, url="https://vllm.test", model_name="whisper-1")
        adapter = AudioTranscriptionsAdapter(provider=provider)
        original_response = ProviderOriginalResponse(data={"text": "hello world"})

        # Act
        result = adapter.format_response(original_request=_original_request(), original_response=original_response)

        # Assert
        assert result.data.text == "hello world"
        assert result.data.model == "audio-router"


class TestMistralAudioTranscriptionsAdapter:
    def test_should_encode_audio_file_into_chat_completions_body(self):
        # Arrange
        provider = ProviderFactory(type=ProviderType.MISTRAL, url="https://mistral.test", model_name="voxtral")
        adapter = MistralAudioTranscriptionsAdapter(provider=provider)

        # Act
        result = adapter.format_request(original_request=_original_request())

        # Assert
        assert result.url == "https://mistral.test/v1/chat/completions"
        assert result.body["model"] == "voxtral"
        assert result.files == {}
        assert result.form == {}
