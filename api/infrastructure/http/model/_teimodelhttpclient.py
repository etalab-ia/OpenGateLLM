from http import HTTPMethod
from typing import Literal

from pydantic import BaseModel, Field

from api.domain.provider.entities import ProviderType
from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.schemas.rerank import RerankResult, Reranks
from api.schemas.usage import Usage
from api.utils.variables import EndpointRoute

from ._modelhttpclient import (
    FormattedModelRequest,
    FormattedModelResponse,
    ModelHttpClient,
    ModelHttpClientEndpoints,
    ModelHttpExchange,
    ModelsAdapter,
    OriginalModelRequest,
    RerankAdapter,
)


class TeiCreateRerankBody(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: Literal["left", "right"] = "right"


class TeiRerankAdapter(RerankAdapter):
    def format_request(self, original_request: OriginalModelRequest, method: HTTPMethod, url: str, model_name: str) -> FormattedModelRequest:
        body = TeiCreateRerankBody(query=original_request.body["query"], texts=original_request.body["documents"]).model_dump()
        return FormattedModelRequest(method=method, url=url, body=body)

    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        results = sorted(exchange.original_response.data, key=lambda x: x["score"], reverse=True)[: exchange.original_request.body.get("top_n")]
        results = [RerankResult(relevance_score=rank["score"], index=rank["index"]) for rank in results]
        return FormattedModelResponse(
            data=Reranks(
                id=request_id,
                model=exchange.original_request.body["model"],
                results=results,
                usage=usage.model_dump() if usage is not None else None,
            )
        )


class TeiModelsAdapter(ModelsAdapter):
    def format_response(self, exchange: ModelHttpExchange, request_id: str, usage: Usage | None) -> FormattedModelResponse:
        return FormattedModelResponse(
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


class TeiModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(
        audio_transcriptions=(None, None),
        chat_completions=(None, None),
        models=(HTTPMethod.GET, "/info"),
        ocr=(None, None),
        rerank=(HTTPMethod.POST, "/rerank"),
    )
    TYPE = ProviderType.TEI

    def _build_adapters(self):
        adapters = super()._build_adapters()
        adapters[EndpointRoute.MODELS] = TeiModelsAdapter()
        adapters[EndpointRoute.RERANK] = TeiRerankAdapter()
        return adapters
