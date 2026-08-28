from enum import StrEnum

from api.domain import BaseModel, EntitiesPage, UtcDatetime


class OrganizationSortField(StrEnum):
    ID = "id"
    NAME = "name"
    CREATED = "created"
    UPDATED = "updated"


class Organization(BaseModel):
    id: int
    name: str
    users: int
    created: UtcDatetime
    updated: UtcDatetime


OrganizationPage = EntitiesPage["Organization"]
