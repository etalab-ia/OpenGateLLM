from pydantic import Field

from api.domain import BaseModel, ForwardablePayload
from api.domain.model.entities import ModelJsonResponse
from api.domain.usage.entities import Usage


class CreateRerankBody(ForwardablePayload):
    query: str
    documents: list[str]
    model: str
    top_n: int | None

    def get_prompts(self) -> list[str]:
        return [self.query] + self.documents


class RerankResult(BaseModel):
    relevance_score: float
    index: int


class Rerank(ModelJsonResponse):
    id: str
    model: str
    results: list[RerankResult]
    usage: Usage = Field(default_factory=Usage)
