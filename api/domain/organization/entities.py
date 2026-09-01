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

    def with_name(self, name: str) -> "Organization":
        return self.model_copy(update={"name": name})


OrganizationPage = EntitiesPage["Organization"]
