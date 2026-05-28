from pydantic import Field

from api.domain import BaseModel
from api.domain.usage.entities import Usage


class CreateRerankBody(BaseModel):
    query: str
    documents: list[str]
    model: str
    top_n: int | None

    def get_prompts(self) -> list[str]:
        return [self.query] + self.documents


class RerankResult(BaseModel):
    relevance_score: float
    index: int


class Rerank(BaseModel):
    id: str
    results: list[RerankResult]
    model: str
    usage: Usage = Field(default_factory=Usage)
