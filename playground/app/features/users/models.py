from pydantic import BaseModel


class User(BaseModel):
    """User model."""

    id: int
    email: str
    name: str | None
    sub: str | None
    iss: str | None
    role: int
    organization: int | None
    budget: float | None
    expires_at: int | None
    created_at: int
    updated_at: int
    priority: int


class FormattedUser(BaseModel):
    """Formatted user for display."""

    id: int
    email: str
    name: str | None
    sub: str | None
    iss: str | None
    role: int
    role_name: str
    organization: int | None
    organization_name: str | None
    budget: float | None
    expires_at: int | None
    created_at: str
    updated_at: str
    priority: int
    expires_at_formatted: str | None
