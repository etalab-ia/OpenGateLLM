from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar


class SortField(StrEnum):
    ID = "id"
    NAME = "name"
    CREATED = "created"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


T = TypeVar("T")


@dataclass
class EntitiesPage(Generic[T]):
    total: int
    data: list[T]
