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


class Document(Entity):
    """Document returned by the OpenGateRAG API."""

    id: int | None = None
    name: str = ""
    collection_id: int | None = None
    created: str | None = None
    chunks: int = 0
    size: int = 0


class Chunk(Entity):
    """Read-only chunk with display-ready provenance metadata."""

    id: int | None = None
    collection_id: int | None = None
    document_id: int | None = None
    content: str = ""
    metadata: dict[str, str | int | float | bool] = {}
    metadata_json: str = "{}"
    page_number: int | None = None
    created: str | None = None
