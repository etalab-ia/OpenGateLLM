from pydantic import ConfigDict, Field

from api.domain import BaseModel
from api.domain.model.entities import ModelCosts, ModelType


class ModelView(BaseModel):
    """Read model of a router exposed as a model by the models API."""

    model_config = ConfigDict(frozen=True)

    router_id: int
    id: str
    type: ModelType
    aliases: list[str] = []
    created: int
    owned_by: str
    max_context_length: int | None = None
    costs: ModelCosts = Field(default_factory=ModelCosts)
