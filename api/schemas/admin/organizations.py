from datetime import datetime
from typing import Literal

from pydantic import Field, constr

from api.schemas import BaseModel


class OrganizationRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(description="The organization name.")


class OrganizationUpdateRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="The new organization name.")


class OrganizationsResponse(BaseModel):
    id: int


class Organization(BaseModel):
    object: Literal["organization"] = "organization"
    id: int
    name: str
    users: int
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class Organizations(BaseModel):
    object: Literal["list"] = "list"
    data: list[Organization]
