from app.shared.models.entities import Entity


class Collection(Entity):
    """Collection returned by the OpenGateRAG API."""

    id: int | None = None
    name: str = ""
    description: str = ""
    owner: int | None = None
    visibility: str = "private"
    documents: int = 0
    size: int = 0
    created: str | None = None
    updated: str | None = None
    is_owner: bool = False
