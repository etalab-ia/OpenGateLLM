from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import Field, constr, field_validator

from app.schemas import BaseModel


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
    model: str = Field(description="Model ID")
    type: LimitType
    value: Optional[int] = Field(default=None, ge=0)


class RoleUpdateRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new role name.")
    permissions: Optional[List[PermissionType]] = Field(default=None, description="The new permissions.")
    limits: Optional[List[Limit]] = Field(default=None, description="The new limits.")

    @field_validator("limits", mode="after")
    def check_duplicate_limits(cls, limits):
        keys = set()
        if limits is not None:
            for limit in limits:
                key = (limit.model, limit.type.value)
                if key in keys:
                    raise ValueError(f"Duplicate limit found: ({limit.model}, {limit.type}).")
                keys.add(key)
        return limits


class RolesResponse(BaseModel):
    id: int


class RoleRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1)
    permissions: Optional[List[PermissionType]] = []
    limits: List[Limit] = []

    @field_validator("limits", mode="after")
    def check_duplicate_limits(cls, limits):
        keys = set()
        for limit in limits:
            key = (limit.model, limit.type.value)
            if key in keys:
                raise ValueError(f"Duplicate limit found: ({limit.model}, {limit.type}).")
            keys.add(key)

        return limits


class Role(BaseModel):
    object: Literal["role"] = "role"
    id: int
    name: str
    permissions: List[PermissionType]
    limits: List[Limit]
    users: int = 0
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class Roles(BaseModel):
    object: Literal["list"] = "list"
    data: List[Role]
