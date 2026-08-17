import datetime as dt
from enum import StrEnum
from typing import Literal

from pydantic import Field, constr, field_validator

from api.schemas import BaseModel


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


class CreateRole(BaseModel):
    name: constr(strip_whitespace=True, min_length=1)
    permissions: list[PermissionType] | None = []
    limits: list[Limit] = []

    @field_validator("limits", mode="after")
    def check_duplicate_limits(cls, limits):
        keys = set()
        for limit in limits:
            key = (limit.router_id, limit.type.value)
            if key in keys:
                raise ValueError(f"Duplicate limit found: ({limit.router_id}, {limit.type}).")
            keys.add(key)

        return limits


class Role(BaseModel):
    object: Literal["role"] = "role"
    id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]
    users: int = 0
    created: int = Field(default_factory=lambda: int(dt.datetime.now().timestamp()))
    updated: int = Field(default_factory=lambda: int(dt.datetime.now().timestamp()))


class Roles(BaseModel):
    object: Literal["list"] = "list"
    data: list[Role]
