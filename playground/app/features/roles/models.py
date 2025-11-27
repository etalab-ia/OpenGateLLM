from app.shared.models.entities import Entity


class Role(Entity):
    """Role model."""

    id: int | None = None
    name: str | None = None
    permissions_admin: bool | None = None
    permissions_create_public_collection: bool | None = None
    permissions_read_metric: bool | None = None
    permissions_provide_models: bool | None = None
    limits: list[dict] | None = None
    users: int | None = None
    created: str | None = None
    updated: str | None = None
