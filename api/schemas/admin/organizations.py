from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field, constr

from api.schemas import BaseModel


class OrganizationRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1) = Field(description="The organization name.")


class OrganizationUpdateRequest(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1)] = Field(default=None, description="The new organization name.")


class OrganizationsResponse(BaseModel):
    id: int


class Organization(BaseModel):
    object: Literal["organization"] = "organization"
    id: int
    name: str
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    updated_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class Organizations(BaseModel):
    object: Literal["list"] = "list"
    data: List[Organization]
