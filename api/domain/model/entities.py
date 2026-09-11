from enum import StrEnum

from api.domain import BaseModel
from api.domain.provider.entities import ProviderJsonResponse
from api.domain.router.entities import RouterType


class ModelCosts(BaseModel):
    prompt_tokens: float = 0.0
    completion_tokens: float = 0.0


# class ModelJsonResponse(BaseModel):
#     def get_completions(self) -> list[str]:
#         return []


class Model(BaseModel):
    id: str
    type: RouterType
    aliases: list[str] = []
    created: int
    owned_by: str
    max_context_length: int | None = None


class Models(ProviderJsonResponse):
    data: list[Model]


class HealthStatus(StrEnum):
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"


class ModelHealthStatus(BaseModel):
    id: str
    status: HealthStatus
