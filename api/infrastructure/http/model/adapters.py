from copy import deepcopy
from http import HTTPMethod

from api.infrastructure.fastapi.schemas.models import ModelsResponse
from api.infrastructure.http.model.exchanges import FormattedModelRequest, FormattedModelResponse, ModelHttpExchange, OriginalModelRequest
from api.schemas.audio import AudioTranscription, AudioTranscriptionResponseFormat
from api.schemas.chat import ChatCompletion
from api.schemas.embeddings import Embeddings
from api.schemas.ocr import OCR
from api.schemas.rerank import Reranks
from api.schemas.usage import Usage


class EndpointAdapter:
    response_type: type

    def format_request(self, original_request: OriginalModelRequest, method: HTTPMethod, url: str, model_name: str) -> FormattedModelRequest:
        body = deepcopy(original_request.body)
        body["model"] = model_name
        return FormattedModelRequest(method=method, url=url, body=body)

    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        data = deepcopy(exchange.original_response.data)
        data.update({"id": request_id, "model": exchange.original_request.body["model"]})
        if usage is not None:
            data.update({"usage": usage.model_dump()})
        return FormattedModelResponse(data=self.response_type(**data))


class AudioTranscriptionAdapter(EndpointAdapter):
    def format_request(self, original_request: OriginalModelRequest, method: HTTPMethod, url: str, model_name: str) -> FormattedModelRequest:
        form = deepcopy(original_request.form)
        form["model"] = model_name
        if form["response_format"] == AudioTranscriptionResponseFormat.TEXT:
            form["response_format"] = AudioTranscriptionResponseFormat.JSON.value
        return FormattedModelRequest(method=method, url=url, form=form, files=original_request.files)

    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        if exchange.original_request.form["response_format"] == AudioTranscriptionResponseFormat.TEXT:
            return FormattedModelResponse(text=exchange.original_response.data["text"])
        data = deepcopy(exchange.original_response.data)
        data.update({"id": request_id, "model": exchange.original_request.form["model"]})
        if usage is not None:
            data.update({"usage": usage.model_dump()})
        return FormattedModelResponse(data=AudioTranscription(**data))


class ChatCompletionAdapter(EndpointAdapter):
    response_type = ChatCompletion


class EmbeddingsAdapter(EndpointAdapter):
    response_type = Embeddings


class ModelsAdapter(EndpointAdapter):
    def format_request(self, original_request: OriginalModelRequest, method: HTTPMethod, url: str, model_name: str) -> FormattedModelRequest:
        return FormattedModelRequest(method=method, url=url)

    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        data = deepcopy(exchange.original_response.data)
        return FormattedModelResponse(data=ModelsResponse(**data))


class OcrAdapter(EndpointAdapter):
    response_type = OCR


class RerankAdapter(EndpointAdapter):
    response_type = Reranks
