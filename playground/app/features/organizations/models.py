from app.shared.models.entities import Entity


class Organization(Entity):
    """Organization model."""

    id: int | None = None
    name: str | None = None
    users: int | None = None
    created: str | None = None
    updated: str | None = None
