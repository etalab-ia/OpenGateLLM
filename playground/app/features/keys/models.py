from app.shared.models.entities import Entity


class Key(Entity):
    """API Key model."""

    id: int | None = None
    name: str | None = None
    token: str | None = None
    expires: str | None = None
    created: str | None = None
