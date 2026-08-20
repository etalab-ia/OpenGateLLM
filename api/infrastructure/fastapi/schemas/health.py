from enum import StrEnum

from api.domain import BaseModel


class HealthStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ModelHealthStatus(BaseModel):
    id: str
    status: HealthStatus


class ModelsHealthResponse(BaseModel):
    data: list[ModelHealthStatus]
