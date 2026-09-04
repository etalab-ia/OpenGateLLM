from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas import UnixTimestamp


class CreateOrganizationBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Name of the organization.", examples=["my-org"])]  # fmt: off


class UpdateOrganizationBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(..., description="Name of the organization.", examples=["my-org"])]  # fmt: off


class OrganizationResponse(BaseModel):
    object: Annotated[Literal["organization"], Field(default="organization", description="Type of the object.")]
    id: Annotated[int, Field(description="ID of the organization.")]
    name: Annotated[str, Field(description="Name of the organization.")]
    users: Annotated[int, Field(description="Number of users in the organization.")]
    created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[UnixTimestamp, Field(description="Time of last update, as Unix timestamp.")]


class OrganizationsResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of the object.")]
    total: Annotated[int, Field(description="Total number of organizations.")]
    offset: Annotated[int, Field(description="Offset of the organizations list.")]
    limit: Annotated[int, Field(description="Limit of the organizations list.")]
    data: Annotated[list[OrganizationResponse], Field(description="List of organizations.")]
