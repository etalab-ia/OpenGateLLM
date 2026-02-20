import os

from fastapi.testclient import TestClient
import pytest
from pytest_snapshot.plugin import Snapshot

from api.schemas.audio import AudioTranscription
from api.schemas.models import ModelType
from api.utils.variables import EndpointRoute


@pytest.fixture(scope="module")
def setup(client: TestClient):
    response = client.get_without_permissions(url=f"/v1{EndpointRoute.MODELS}")
    assert response.status_code == 200, f"error: retrieve models ({response.status_code})"
    response_json = response.json()
    model = [model for model in response_json["data"] if model["type"] == ModelType.AUTOMATIC_SPEECH_RECOGNITION][0]
    MODEL_ID = model["id"]

    yield MODEL_ID


@pytest.mark.usefixtures("client", "setup")
class TestAudio:
    def test_audio_transcriptions_mp3(self, client: TestClient, setup: str) -> None:
        """Test the POST /audio/transcriptions endpoint with MP3 file"""
        MODEL_ID = setup

        file_path = "api/tests/integ/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "json", "temperature": 0}
            response = client.post_without_permissions(f"/v1{EndpointRoute.AUDIO_TRANSCRIPTIONS}", files=files, data=data)

        assert response.status_code == 200, response.text
        AudioTranscription(**response.json())  # test output format

    def test_audio_transcriptions_text_output(self, client: TestClient, setup: str) -> None:
        """Test the POST /audio/transcriptions with text output"""
        MODEL_ID = setup

        file_path = "api/tests/integ/assets/audio.mp3"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "text"}
            response = client.post_without_permissions(f"/v1{EndpointRoute.AUDIO_TRANSCRIPTIONS}", files=files, data=data)

        assert response.status_code == 200, response.text
        assert isinstance(response.text, str)

    def test_audio_transcriptions_wav(self, client: TestClient, setup: str) -> None:
        """Test the POST /audio/transcriptions endpoint with WAV file"""
        MODEL_ID = setup

        file_path = "api/tests/integ/assets/audio.wav"
        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/wav")}
            data = {"model": MODEL_ID, "language": "fr", "response_format": "json", "temperature": 0}
            response = client.post_without_permissions(f"/v1{EndpointRoute.AUDIO_TRANSCRIPTIONS}", files=files, data=data)

        assert response.status_code == 200, response.text
        AudioTranscription(**response.json())  # test output format

    def test_audio_transcriptions_invalid_model(self, client: TestClient, setup: str, snapshot: Snapshot) -> None:
        """Test the POST /audio/transcriptions with invalid model"""
        file_path = "api/tests/integ/assets/audio.mp3"

        with open(file_path, "rb") as file:
            files = {"file": (os.path.basename(file_path), file, "audio/mpeg")}
            data = {"model": "invalid-model", "language": "fr"}
            response = client.post_without_permissions(f"/v1{EndpointRoute.AUDIO_TRANSCRIPTIONS}", files=files, data=data)

        assert response.status_code == 404, response.text
        snapshot.assert_match(str(response.text), snapshot_name="audio_transcriptions_invalid_model")
