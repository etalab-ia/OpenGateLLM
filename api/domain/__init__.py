from abc import ABC
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


class BaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


def _to_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(tz=UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_to_utc)]


class ForwardablePayload(BaseModel, ABC):
    """The client's request body. Only what the use case reads is declared; every other field passes through
    to the provider, since the base model allows extra fields."""

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
