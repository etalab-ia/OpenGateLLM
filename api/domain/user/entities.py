from enum import StrEnum
from typing import Any

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
    claims: dict[str, Any] | None
    role: int
    organization_id: int | None
    budget: float | None
    expires: int | None
    created: int
    updated: int
    priority: int
    password: SecretStr | None

    def need_to_update(
        self,
        email: str,
        name: str | None,
        iss: str | None,
        sub: str | None,
        claims: dict[str, Any],
        organization_id: int | None,
        role_id: int | None,
    ) -> bool:
        return (
            self.email != email
            or self.claims != claims
            or self.name != name
            or self.organization_id != organization_id
            or self.role != role_id
            or self.iss != iss
            or self.sub != sub
        )
