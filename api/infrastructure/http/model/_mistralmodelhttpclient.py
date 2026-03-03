import base64

from mistralai.client.models import AudioChunk, ChatCompletionRequest, TextChunk, UserMessage

from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints
from api.schemas.audio import AudioTranscription
from api.schemas.core.models import RequestContent


class MistralModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(audio_transcriptions="/v1/chat/completions", rerank=None)

    # request formatting
    @staticmethod
    def format_chat_completion_request(request_content: RequestContent) -> RequestContent:
        # see https://docs.mistral.ai/api#operation-chat_completion_v1_chat_completions_post
        request_content.body = {
            "frequency_penalty": request_content.body.get("frequency_penalty") or 0.0,
            "max_tokens": request_content.body.get("max_tokens"),
            "messages": request_content.body.get("messages"),
            "model": request_content.body.get("model"),
            "n": request_content.body.get("n"),
            "parallel_tool_calls": request_content.body.get("parallel_tool_calls") or False,
            "prediction": request_content.body.get("prediction") or {},
            "presence_penalty": request_content.body.get("presence_penalty") or 0.0,
            "prompt_mode": request_content.body.get("prompt_mode"),
            "random_seed": request_content.body.get("random_seed") or request_content.body.get("seed"),
            "response_format": request_content.body.get("response_format") or {"type": "text"},
            "safe_prompt": request_content.body.get("safe_prompt") or False,
            "stop": request_content.body.get("stop") or [],
            "stream": request_content.body.get("stream") or False,
            "temperature": request_content.body.get("temperature"),
            "tool_choice": request_content.body.get("tool_choice"),
            "tools": request_content.body.get("tools"),
            "top_p": request_content.body.get("top_p") or 1.0,
        }

        return request_content

    @staticmethod
    def format_audio_transcription_request(request_content: RequestContent) -> RequestContent:
        text = request_content.form.get("prompt") or f"Transcribe this audio in this language : {request_content.form.get('language', 'en')}"
        input_audio = base64.b64encode(request_content.files["file"][1]).decode("utf-8")
        request_content.body = ChatCompletionRequest(
            model=request_content.form["model"],
            messages=[
                UserMessage(
                    role="user",
                    content=[AudioChunk(type="input_audio", input_audio=input_audio), TextChunk(type="text", text=text)],
                )
            ],
            temperature=request_content.form.get("temperature"),
        ).model_dump()
        request_content.files = {}
        request_content.form = {}

        return request_content

    # response formatting
    @staticmethod
    def format_response_to_models_response(request_content: RequestContent, response_data: dict) -> ModelsResponse:
        return ModelsResponse(
            data=[
                ModelResponse(
                    id=model.get("id"),
                    created=model.get("created"),
                    owned_by=model.get("owned_by"),
                    max_context_length=model.get("max_context_length"),
                    aliases=model.get("aliases", []),
                )
                for model in response_data.get("data", [])
            ]
        )

    @staticmethod
    def format_response_to_audio_transcription_response(request_content: RequestContent, response_data: dict) -> AudioTranscription:
        return AudioTranscription(
            id=response_data["id"],
            model=response_data["model"],
            text=response_data["choices"][0]["message"]["content"],
            usage=response_data["usage"],
        )
