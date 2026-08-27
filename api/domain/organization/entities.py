from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from api.domain import EntitiesPage


class OrganizationSortField(StrEnum):
    ID = "id"
    NAME = "name"
    CREATED = "created"
    UPDATED = "updated"


@dataclass
class Organization:
    id: int
    name: str
    users: int
    created: datetime
    updated: datetime


OrganizationPage = EntitiesPage["Organization"]
