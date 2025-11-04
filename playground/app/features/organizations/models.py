"""Organization models."""

from pydantic import BaseModel


class Organization(BaseModel):
    """Organization model matching API schema."""

    id: int
    name: str
    created_at: int
    updated_at: int


class FormattedOrganization(BaseModel):
    """Organization with formatted dates for display."""

    id: int
    name: str
    created_at: str
    updated_at: str
