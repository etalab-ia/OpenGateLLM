from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar


class SortField(str, Enum):
    ID = "id"
    NAME = "name"
    CREATED = "created"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


T = TypeVar("T")


@dataclass
class EntitiesPage(Generic[T]):
    total: int
    data: list[T]
