from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from api.domain import EntitiesPage, UtcDatetime


class PermissionType(StrEnum):
    ADMIN = "admin"
    READ_METRIC = "read_metric"
    PROVIDE_MODELS = "provide_models"


class LimitType(StrEnum):
    TPM = "tpm"
    TPD = "tpd"
    RPM = "rpm"
    RPD = "rpd"


class Limit(BaseModel):
    router_id: int = Field(description="The router ID.")
    type: LimitType = Field(description="The limit type.")
    value: int | None = Field(default=None, ge=0, description="The limit value.")


class Role(BaseModel):
    id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]
    users: int = 0
    created: UtcDatetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated: UtcDatetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    @field_validator("permissions")
    @classmethod
    def unique_permissions(cls, permissions: list[PermissionType]) -> list[PermissionType]:
        return list(dict.fromkeys(permissions))

    @field_validator("limits")
    @classmethod
    def unique_limits(cls, limits: list["Limit"]) -> list["Limit"]:
        return list({(limit.router_id, limit.type): limit for limit in limits}.values())

    def with_name(self, name: str) -> "Role":
        return self.model_copy(update={"name": name})

    def with_limits(self, limits: list["Limit"]) -> "Role":
        return self.model_copy(update={"limits": limits})

    def with_permissions(self, permissions: list["PermissionType"]) -> "Role":
        return self.model_copy(update={"permissions": permissions})


RolePage = EntitiesPage["Role"]
