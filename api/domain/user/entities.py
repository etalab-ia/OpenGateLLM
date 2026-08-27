from enum import StrEnum
from typing import Any

from pydantic import BaseModel, SecretStr

from api.domain import EntitiesPage, UtcDatetime


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
    role_id: int
    organization_id: int | None
    budget: float | None
    expires: UtcDatetime | None
    created: UtcDatetime
    updated: UtcDatetime
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
            or self.role_id != role_id
            or self.iss != iss
            or self.sub != sub
        )
