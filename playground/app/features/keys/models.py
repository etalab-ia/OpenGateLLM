"""API Keys models."""

from pydantic import BaseModel


class ApiKey(BaseModel):
    """API Key model."""

    id: int
    name: str
    token: str
    expires: int | None = None
    created: int


class FormattedApiKey(BaseModel):
    """API Key with formatted dates for display."""

    id: int
    name: str
    token: str
    created: str
    expires: str


class Limit(BaseModel):
    """User limit model."""

    model: str
    type: str  # TPM, TPD, RPM, RPD
    value: int | None = None
