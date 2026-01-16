import datetime as dt
from json.decoder import JSONDecodeError
import os

from fastapi.testclient import TestClient
import pytest

from api.schemas.admin.providers import ProviderType
from api.schemas.audio import AudioTranscription
from api.schemas.models import ModelType
from api.tests.integ.utils import (
    create_provider,
    create_role,
    create_router,
    create_token,
    create_user,
    generate_test_id,
    kill_openmockllm,
    run_openmockllm,
)
from api.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS


@pytest.fixture(scope="module")
def setup_mistral_automatic_speech_recognition_model(client: TestClient):
    test_id = generate_test_id(prefix="TestMistralAutomaticSpeechRecognition")
    process = run_openmockllm(test_id=test_id, backend="mistral")
    try:
        router_id = create_router(model_name=process.model_name, model_type=ModelType.AUTOMATIC_SPEECH_RECOGNITION, client=client)
        create_provider(
            router_id=router_id,
            provider_url=process.url,
            provider_key=None,
            provider_name=process.model_name,
            provider_type=ProviderType.MISTRAL,
            client=client,
        )
        role_id = create_role(router_id=router_id, client=client)
        user_id = create_user(role_id=role_id, client=client)
        _, key = create_token(user_id=user_id, token_name=f"test-token-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}", client=client)

        yield key, process.model_name
    except Exception as e:
        raise e
    finally:
        kill_openmockllm(process=process)


@pytest.mark.usefixtures("client", "setup_mistral_automatic_speech_recognition_model")
class TestMistralAutomaticSpeechRecognition:
    def test_audio_transcriptions_mp3_successful(self, client: TestClient, setup_mistral_automatic_speech_recognition_model: tuple[str, str]) -> None:
        """Test the POST /audio/transcriptions endpoint with MP3 file"""
        api_key, model_name = setup_mistral_automatic_speech_recognition_model

        file_path = "api/tests/integ/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mp3")}
            data = {"model": model_name, "language": "fr", "temperature": 0}
            response = client.post(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}", files=files, data=data, headers={"Authorization": f"Bearer {api_key}"})

        assert response.status_code == 200, response.text
        response_data = response.json()
        transcription = AudioTranscription(**response_data)

        assert transcription.text is not None
        assert len(transcription.text) > 0
        assert len(response_data.get("id")) > 0

    def test_audio_transcriptions_mp3_text_output_successful(
        self, client: TestClient, setup_mistral_automatic_speech_recognition_model: tuple[str, str]
    ) -> None:
        """Test the POST /audio/transcriptions with text output"""
        api_key, model_name = setup_mistral_automatic_speech_recognition_model

        file_path = "api/tests/integ/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mp3")}
            data = {"model": model_name, "language": "fr", "response_format": "text"}
            response = client.post(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}", files=files, data=data, headers={"Authorization": f"Bearer {api_key}"})

        assert response.status_code == 200, response.text
        try:
            response.json()
            assert False, "Response is valid JSON"
        except JSONDecodeError:
            pass

        assert isinstance(response.text, str)
        assert len(response.text) > 0

    def test_audio_transcriptions_wav_successful(self, client: TestClient, setup_mistral_automatic_speech_recognition_model: tuple[str, str]) -> None:
        """Test the POST /audio/transcriptions endpoint with WAV file"""
        api_key, model_name = setup_mistral_automatic_speech_recognition_model

        file_path = "api/tests/integ/assets/audio.wav"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/wav")}
            data = {"model": model_name, "language": "fr", "response_format": "json", "temperature": 0}
            response = client.post(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}", files=files, data=data, headers={"Authorization": f"Bearer {api_key}"})

        assert response.status_code == 200, response.text
        response_data = response.json()
        transcription = AudioTranscription(**response_data)

        assert transcription.text is not None
        assert isinstance(transcription.text, str)
        assert len(transcription.text) > 0

    def test_audio_transcriptions_invalid_response_format(
        self,
        client: TestClient,
        setup_mistral_automatic_speech_recognition_model: tuple[str, str],
    ) -> None:
        """Test the POST /audio/transcriptions endpoint with invalid response format"""
        api_key, model_name = setup_mistral_automatic_speech_recognition_model

        file_path = "api/tests/integ/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mp3")}
            data = {"model": model_name, "language": "fr", "response_format": "invalid_format"}
            response = client.post(f"/v1{ENDPOINT__AUDIO_TRANSCRIPTIONS}", files=files, data=data, headers={"Authorization": f"Bearer {api_key}"})

        assert response.status_code == 422
