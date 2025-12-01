from app.shared.models.entities import Entity


class User(Entity):
    """User model."""

    id: int | None = None
    email: str | None = None
    name: str | None = None
    password: str | None = None
    role: str | None = None
    organization: str | None = None
    budget: float | None = None
    priority: int | None = None
    expires: str | None = None
    created: str | None = None
    updated: str | None = None
