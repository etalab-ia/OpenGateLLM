from pydantic import BaseModel


class Entity(BaseModel):
    """Entity model."""

    id: int | None = None
