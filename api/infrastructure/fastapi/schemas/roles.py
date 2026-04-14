from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from api.schemas import BaseModel


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
    router_id: Annotated[int, Field(alias="router_id", description="The router ID.")]
    type: Annotated[LimitType, Field(description="The limit type.")]
    value: Annotated[int | None, Field(default=None, ge=0, description="The limit value.")]


class CreateRoleBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Name of the role.", examples=["my-role"])]
    permissions: Annotated[list[PermissionType] | None, Field(default=None, description="List of permissions.")]
    limits: Annotated[list[Limit] | None, Field(default=None, description="List of limits.")]


class RoleResponse(BaseModel):
    object: Annotated[Literal["role"], Field("role", description="Type of the object.")]
    id: Annotated[int, Field(..., description="ID of the role.")]
    name: Annotated[str, Field(..., description="Name of the role.")]
    permissions: Annotated[list[PermissionType], Field(..., description="List of permissions.")]
    limits: Annotated[list[Limit], Field(..., description="List of limits.")]
    users: Annotated[int, Field(..., description="Number of users assigned to the role.")]
    created: Annotated[int, Field(..., description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(..., description="Time of last update, as Unix timestamp.")]
