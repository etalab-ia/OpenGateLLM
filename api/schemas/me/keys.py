from typing import Literal

from api.schemas import BaseModel


class Key(BaseModel):
    object: Literal["key"] = "key"
    id: int
    name: str
    token: str
    expires: int | None = None
    created: int
