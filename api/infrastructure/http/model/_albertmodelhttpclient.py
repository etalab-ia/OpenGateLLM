from api.infrastructure.http.model._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints
from api.schemas.audio import AudioTranscriptionResponseFormat
from api.schemas.core.models import RequestContent


class AlbertModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints()

    # request formatting
    @staticmethod
    def format_audio_transcription_request(request_content: RequestContent) -> RequestContent:
        if request_content.form["response_format"] == AudioTranscriptionResponseFormat.TEXT:
            # @TODO: remove this once the Albert API supports the text response format
            request_content.form["response_format"] = AudioTranscriptionResponseFormat.JSON.value

        return request_content
