"""Organization models."""

from pydantic import BaseModel


class Organization(BaseModel):
    """Organization model matching API schema."""

    id: int
    name: str
    users: int
    created: int
    updated: int


class FormattedOrganization(BaseModel):
    """Organization with formatted dates for display."""

    id: int
    name: str
    users: int
    created: str
    updated: str
