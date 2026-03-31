import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class PermissionType(StrEnum):
    ADMIN = "admin"
    CREATE_PUBLIC_COLLECTION = "create_public_collection"
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
