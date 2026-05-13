from enum import StrEnum

from pydantic import BaseModel

from api.domain import EntitiesPage
from api.domain.model.entities import ModelType as RouterType


class RouterLoadBalancingStrategy(StrEnum):
    SHUFFLE = "shuffle"
    LEAST_BUSY = "least_busy"


RouterPage = EntitiesPage["Router"]


class Router(BaseModel):
    id: int
    name: str
    user_id: int
    type: RouterType
    aliases: list[str] | None
    load_balancing_strategy: RouterLoadBalancingStrategy
    vector_size: int | None
    max_context_length: int | None
    cost_prompt_tokens: float
    cost_completion_tokens: float
    providers: int
    created: int
    updated: int

    def with_name(self, name: str) -> "Router":
        return self.model_copy(update={"name": name})

    def with_type(self, router_type: RouterType) -> "Router":
        return self.model_copy(update={"type": router_type})

    def with_load_balancing_strategy(self, strategy: RouterLoadBalancingStrategy) -> "Router":
        return self.model_copy(update={"load_balancing_strategy": strategy})

    def with_cost_prompt_tokens(self, prompt_tokens: float) -> "Router":
        return self.model_copy(update={"cost_prompt_tokens": prompt_tokens})

    def with_cost_completion_tokens(self, completion_tokens: float) -> "Router":
        return self.model_copy(update={"cost_completion_tokens": completion_tokens})

    def with_aliases(self, aliases: list[str]) -> "Router":
        return self.model_copy(update={"aliases": aliases})

    def vector_size_is_consistent(self, vector_size: int) -> bool:
        return self.vector_size == vector_size

    def max_context_length_is_consistent(self, max_context_length) -> bool:
        return self.max_context_length == max_context_length

    @property
    def has_providers(self) -> bool:
        return self.providers > 0
