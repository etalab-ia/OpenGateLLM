from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from api.schemas import BaseModel
from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import RequestContent, TEICreateRerank
from api.schemas.usage import Usage


class CreateRerank(BaseModel):
    query: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True), Field(description="The search query to use for the reranking. `query` and `prompt` cannot both be provided.")]  # fmt: off
    documents: list[Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)], Field(description="A list of texts that will be compared to the query and ranked by relevance. `documents` and `input` cannot both be provided.")]  # fmt: off
    model: Annotated[str, StringConstraints(min_length=1, strip_whitespace=True), Field(default=..., description="The model to use for the reranking, call `/v1/models` endpoint to get the list of available models, only `text-classification` model type is supported.")]  # fmt: off
    top_n: Annotated[int | None, Field(default=None, ge=1, description="The number of top results to return. If set to None, all results will be returned.")]  # fmt: off

    @staticmethod
    def format_request(provider_type: ProviderType, request_content: RequestContent):
        match provider_type:
            case ProviderType.ALBERT:
                return request_content

            case ProviderType.TEI:
                request_content.additional_data["top_n"] = request_content.json.get("top_n")
                request_content.json = TEICreateRerank(query=request_content.json["query"], texts=request_content.json["documents"]).model_dump()

                return request_content

            case ProviderType.VLLM:
                return request_content

            case _:
                raise NotImplementedError(f"Provider {provider_type} not implemented")


class Rerank(BaseModel):
    object: Annotated[Literal["rerank"], Field(default="rerank", description="The type of the object.")]
    score: Annotated[float, Field(description="The score of the reranked text.")]
    index: Annotated[int, Field(description="The index of the reranked text.")]


class RerankResult(BaseModel):
    relevance_score: Annotated[float, Field(description="The relevance score of the reranked text.")]
    index: Annotated[int, Field(description="The index of the reranked text.")]


class Reranks(BaseModel):
    object: Literal["list"] = "list"
    id: Annotated[str, Field(default=..., description="A unique identifier for the request.")]
    results: Annotated[list[RerankResult], Field(default=..., description="The list of reranked texts.")]
    model: Annotated[str, Field(default=..., description="The model used to generate the reranking.")]
    usage: Annotated[Usage, Field(default_factory=Usage, description="Usage information for the request.")]

    @classmethod
    def build_from(cls, provider_type: ProviderType, request_content: RequestContent, response_data: dict):
        match provider_type:
            case ProviderType.ALBERT:
                response_data.update(request_content.additional_data)
                return cls(**response_data)

            case ProviderType.TEI:
                data = []
                results = []
                if request_content.additional_data["top_n"] is not None:
                    response_data = sorted(response_data, key=lambda x: x["score"], reverse=True)[: request_content.additional_data.get("top_n")]
                    request_content.additional_data.pop("top_n")
                for rank in response_data:
                    results.append(RerankResult(relevance_score=rank["score"], index=rank["index"]))
                return cls(results=results, **request_content.additional_data)

            case ProviderType.VLLM:
                response_data.update(request_content.additional_data)
                return cls(**response_data)

            case _:
                raise NotImplementedError(f"Provider {provider_type} not implemented")
