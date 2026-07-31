from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class BaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ForwardableBody(BaseModel, ABC):
    model: str | None = None

    @abstractmethod
    def get_prompts(self) -> list[str]:
        pass


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
