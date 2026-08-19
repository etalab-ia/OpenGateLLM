import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from api.domain import EntitiesPage


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
    # TODO: add created and updated timestamps after convert int to datetime in all the repositories

    @field_validator("permissions")
    @classmethod
    def unique_permissions(cls, v: list[PermissionType]) -> list[PermissionType]:
        return list(dict.fromkeys(v))

    @field_validator("limits")
    @classmethod
    def unique_limits(cls, v: list["Limit"]) -> list["Limit"]:
        return list({(limit.router_id, limit.type): limit for limit in v}.values())

    users: int = 0
    created: int = Field(default_factory=lambda: int(dt.datetime.now().timestamp()))
    updated: int = Field(default_factory=lambda: int(dt.datetime.now().timestamp()))

    def with_name(self, name: str | None) -> "Role":
        return self.model_copy(update={"name": name})

    def with_limits(self, limits: list["Limit"]) -> "Role":
        return self.model_copy(update={"limits": limits})

    def with_permissions(self, permissions: list["PermissionType"]) -> "Role":
        return self.model_copy(update={"permissions": permissions})


RolePage = EntitiesPage["Role"]
