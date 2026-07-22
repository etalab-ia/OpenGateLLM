from enum import StrEnum

from pydantic import BaseModel, SecretStr

from api.domain import EntitiesPage


class UserSortField(StrEnum):
    ID = "id"
    EMAIL = "email"
    CREATED = "created"
    UPDATED = "updated"


UserPage = EntitiesPage["User"]


class User(BaseModel):
    id: int
    email: str
    name: str | None
    sub: str | None
    iss: str | None
    role: int
    organization_id: int | None
    budget: float | None
    expires: int | None
    created: int
    updated: int
    priority: int
    password: SecretStr | None
