from http import HTTPMethod
from typing import Literal

from pydantic import BaseModel, Field

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.schemas.rerank import RerankResult, Reranks

from ._modelhttpclient import FormattedModelRequest, FormattedModelResponse, ModelHttpClient, ModelHttpClientEndpoints, ModelHttpExchange


class TeiCreateRerankBody(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: Literal["left", "right"] = "right"


class TeiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(
        audio_transcriptions=None,
        chat_completions=None,
        models=(HTTPMethod.GET, "/info"),
        ocr=None,
        rerank=(HTTPMethod.POST, "/rerank"),
    )
    TYPE = ProviderType.TEI

    # request formatting
    def format_rerank_request(self, exchange: ModelHttpExchange) -> ModelHttpExchange:

        body = TeiCreateRerankBody(query=exchange.original_request.body["query"], texts=exchange.original_request.body["documents"]).model_dump()
        exchange.formatted_request = FormattedModelRequest(
            method=self.ENDPOINT_TABLE.rerank[0],
            endpoint=self.ENDPOINT_TABLE.rerank[1],
            body=body,
        )
        return exchange

    # response formatting
    def format_response_to_models_response(self, exchange: ModelHttpExchange) -> ModelHttpExchange:
        exchange.formatted_response = FormattedModelResponse(
            data=ModelsResponse(
                data=[
                    ModelResponse(
                        id=exchange.original_response.data["model_id"],
                        created=0,
                        owned_by="tei",
                        max_context_length=exchange.original_response.data["max_input_length"],
                    )
                ]
            )
        )
        return exchange

    def format_response_to_rerank_response(self, exchange: ModelHttpExchange) -> ModelHttpExchange:
        request_id = self._get_request_id(exchange=exchange)
        usage = self._get_usage(exchange=exchange)
        if usage is not None:
            usage = usage.model_dump()

        results = sorted(exchange.original_response.data, key=lambda x: x["score"], reverse=True)[: exchange.original_request.body.get("top_n")]
        results = [RerankResult(relevance_score=rank["score"], index=rank["index"]) for rank in results]

        exchange.formatted_response = FormattedModelResponse(
            data=Reranks(
                id=request_id,
                model=exchange.original_request.body["model"],
                results=results,
                usage=usage,
            )
        )
        return exchange
