from typing import Literal

from pydantic import Field, constr, model_validator

from api.schemas import BaseModel
from api.schemas.admin.providers import ProviderType
from api.schemas.core.models import RequestContent, TEICreateRerank
from api.schemas.usage import Usage


class CreateRerank(BaseModel):
    prompt: constr(min_length=1, strip_whitespace=True) | None = Field(default=None, description="The prompt to use for the reranking. `query` and `prompt` cannot both be provided.", deprecated=True)  # fmt: off
    query: constr(min_length=1, strip_whitespace=True) | None = Field(default=None, description="The search query to use for the reranking. `query` and `prompt` cannot both be provided.")  # fmt: off
    input: list[constr(min_length=1, strip_whitespace=True)] | None = Field(default=None, description="List of input texts to rerank by relevance to the prompt. `documents` and `input` cannot both be provided.", deprecated=True)  # fmt: off
    documents: list[constr(min_length=1, strip_whitespace=True)] | None = Field(default=None, description="A list of texts that will be compared to the query and ranked by relevance. `documents` and `input` cannot both be provided.")  # fmt: off
    model: constr(min_length=1, strip_whitespace=True) = Field(default=..., description="The model to use for the reranking, call `/v1/models` endpoint to get the list of available models, only `text-classification` model type is supported.")  # fmt: off
    top_n: int | None = Field(default=None, ge=0, description="The number of top results to return. If set to 0, all results will be returned.")  # fmt: off

    @model_validator(mode="after")
    def validate_model(self):
        if self.query and self.prompt:
            raise ValueError("query and prompt cannot both be provided")
        if self.query is None and self.prompt is None:
            raise ValueError("query or prompt must be provided")
        if self.documents and self.input:
            raise ValueError("documents and input cannot both be provided")
        if self.documents is None and self.input is None:
            raise ValueError("documents or input must be provided")

        return self

    @staticmethod
    def format_request(provider_type: ProviderType, request_content: RequestContent):
        match provider_type:
            case ProviderType.ALBERT:
                return request_content

            case ProviderType.TEI:
                request_content.additional_data["top_n"] = request_content.json.get("top_n")
                query = request_content.json.get("query") or request_content.json.get("prompt")
                texts = request_content.json.get("input") or request_content.json.get("documents")
                request_content.json = TEICreateRerank(query=query, texts=texts).model_dump()

                return request_content

            case _:
                raise NotImplementedError(f"Provider {provider_type} not implemented")


class Rerank(BaseModel):
    object: Literal["rerank"] = "rerank"
    score: float
    index: int


class RerankResult(BaseModel):
    relevance_score: float
    index: int


class Reranks(BaseModel):
    object: Literal["list"] = "list"
    id: str = Field(default=..., description="A unique identifier for the request.")
    data: list[Rerank] = Field(default=..., description="The list of reranked texts.", deprecated=True)
    results: list[RerankResult] = Field(default=..., description="The list of reranked texts.")
    model: str = Field(default=..., description="The model used to generate the reranking.")
    usage: Usage = Field(default_factory=Usage, description="Usage information for the request.")

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
                    data.append(Rerank(index=rank["index"], score=rank["score"]))
                    results.append(RerankResult(relevance_score=rank["score"], index=rank["index"]))
                return cls(data=data, results=results, **request_content.additional_data)

            case _:
                raise NotImplementedError(f"Provider {provider_type} not implemented")
