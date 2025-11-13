from pydantic import BaseModel


class Limit(BaseModel):
    """Limit model."""

    model: str
    type: str  # "tpm", "tpd", "rpm", "rpd"
    value: int | None


class Role(BaseModel):
    """Role model."""

    id: int
    name: str
    permissions: list[str]
    limits: list[Limit]
    users: int
    created: int
    updated: int


class FormattedRole(BaseModel):
    """Formatted role for display."""

    id: int
    name: str
    permissions: list[str]
    limits: list[Limit]
    users: int
    created: str
    updated: str
