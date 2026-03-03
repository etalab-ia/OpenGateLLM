from typing import Literal

from pydantic import BaseModel, Field

from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints
from api.schemas.core.models import RequestContent
from api.schemas.rerank import RerankResult, Reranks


class TeiCreateRerankBody(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: Literal["left", "right"] = "right"


class TeiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(audio_transcriptions=None, chat_completions=None, models="/info", ocr=None, rerank="/rerank")

    @staticmethod
    def format_rerank_request(request_content: RequestContent) -> RequestContent:
        request_content.additional_data["top_n"] = request_content.body.get("top_n")
        request_content.body = TeiCreateRerankBody(query=request_content.body["query"], texts=request_content.body["documents"]).model_dump()
        return request_content

    @staticmethod
    def format_rerank_response(request_content: RequestContent, response_data: dict) -> Reranks:
        # @TODO: add model copy (after move additional data logic into format_response_to_* methods)
        response_data = sorted(response_data, key=lambda x: x["score"], reverse=True)[: request_content.additional_data.get("top_n")]
        request_content.additional_data.pop("top_n")
        results = [RerankResult(relevance_score=rank["score"], index=rank["index"]) for rank in response_data]
        return Reranks(results=results, **request_content.additional_data)

    # response formatting
    @staticmethod
    def format_response_to_models_response(request_content: RequestContent, response_data: dict) -> ModelsResponse:
        data = [
            ModelResponse(
                id=response_data.get("model_id", ""),
                created=0,
                owned_by="tei",
                max_context_length=response_data.get("max_input_length"),
            )
        ]
        return ModelsResponse(data=data)
