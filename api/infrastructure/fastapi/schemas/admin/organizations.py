from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from api.domain import BaseModel
from api.domain.organization.entities import Organization


class CreateOrganizationBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Name of the organization.", examples=["my-org"])]  # fmt: off


class OrganizationResponse(BaseModel):
    object: Annotated[Literal["organization"], Field(default="organization", description="Type of the object.")]
    id: Annotated[int, Field(description="ID of the organization.")]
    name: Annotated[str, Field(description="Name of the organization.")]
    users: Annotated[int, Field(description="Number of users in the organization.")]
    created: Annotated[int, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(description="Time of last update, as Unix timestamp.")]

    @model_validator(mode="before")
    @classmethod
    def from_organization(cls, data):
        if isinstance(data, Organization):
            return {
                "object": "organization",
                "id": data.id,
                "name": data.name,
                "users": data.users,
                "created": int(data.created.timestamp()),
                "updated": int(data.updated.timestamp()),
            }
        return data
