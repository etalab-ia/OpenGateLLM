"""Organization models."""

from pydantic import BaseModel


class Organization(BaseModel):
    """Organization model matching API schema."""

    id: int
    name: str
    created: int
    updated: int


class FormattedOrganization(BaseModel):
    """Organization with formatted dates for display."""

    id: int
    name: str
    created: str
    updated: str
