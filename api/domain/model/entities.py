from enum import StrEnum

from api.domain import BaseModel
from api.domain.provider.entities import Provider


class ModelCosts(BaseModel):
    prompt_tokens: float = 0.0
    completion_tokens: float = 0.0


YELLOW_LOAD_RATIO = 0.95


class HealthStatus(StrEnum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

    @classmethod
    def of_provider(cls, provider: Provider, is_live: bool, load: int | None) -> "HealthStatus":
        if not is_live or provider.is_closed:
            return cls.RED
        if load is None or provider.qos_limit is None:
            return cls.GREEN
        if load >= provider.qos_limit:
            return cls.RED
        if load >= YELLOW_LOAD_RATIO * provider.qos_limit:
            return cls.YELLOW
        return cls.GREEN

    @classmethod
    def best_of(cls, statuses: list["HealthStatus"]) -> "HealthStatus":
        return next((status for status in cls if status in statuses), cls.RED)


class ModelHealthStatus(BaseModel):
    id: str
    status: HealthStatus
