from enum import StrEnum

from api.domain import BaseModel


class ModelCosts(BaseModel):
    prompt_tokens: float = 0.0
    completion_tokens: float = 0.0


class HealthStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ModelHealthStatus(BaseModel):
    id: str
    status: HealthStatus
