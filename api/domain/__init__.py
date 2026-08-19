from abc import ABC
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ForwardablePayload(BaseModel, ABC):
    model: str | None

    def get_prompts(self) -> list[str]:
        return []


class SortField(StrEnum):
    ID = "id"
    NAME = "name"
    CREATED = "created"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


@dataclass
class EntitiesPage[T]:
    total: int
    data: list[T]
