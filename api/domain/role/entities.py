import datetime as dt
from enum import Enum

from pydantic import BaseModel, Field


class PermissionType(str, Enum):
    ADMIN = "admin"
    CREATE_PUBLIC_COLLECTION = "create_public_collection"
    READ_METRIC = "read_metric"
    PROVIDE_MODELS = "provide_models"


class LimitType(str, Enum):
    TPM = "tpm"
    TPD = "tpd"
    RPM = "rpm"
    RPD = "rpd"


class Limit(BaseModel):
    router: int = Field(description="The router ID.")
    type: LimitType = Field(description="The limit type.")
    value: int | None = Field(default=None, ge=0, description="The limit value.")


class Role(BaseModel):
    id: int
    name: str
    permissions: list[PermissionType]
    limits: list[Limit]
    users: int = 0
    created: int = Field(default_factory=lambda: int(dt.datetime.now().timestamp()))
    updated: int = Field(default_factory=lambda: int(dt.datetime.now().timestamp()))
