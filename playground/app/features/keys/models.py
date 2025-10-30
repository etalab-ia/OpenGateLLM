"""API Keys models."""

from pydantic import BaseModel


class ApiKey(BaseModel):
    """API Key model."""

    id: int
    name: str
    token: str
    expires_at: int | None = None
    created_at: int


class FormattedApiKey(BaseModel):
    """API Key with formatted dates for display."""

    id: int
    name: str
    token: str
    created_at: str
    expires_at: str


class Limit(BaseModel):
    """User limit model."""

    model: str
    type: str  # TPM, TPD, RPM, RPD
    value: int | None = None
