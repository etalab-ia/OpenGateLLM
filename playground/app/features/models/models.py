from pydantic import BaseModel


class Provider(BaseModel):
    """Provider model."""

    id: int
    router_id: int
    user_id: int
    type: str
    url: str
    key: str | None
    timeout: int
    model_name: str
    model_carbon_footprint_zone: str | None = None
    model_carbon_footprint_total_params: int | None = None
    model_carbon_footprint_active_params: int | None = None
    qos_metric: str | None = None
    qos_limit: float | None = None
    created: int | None = None
    updated: int | None = None


class Router(BaseModel):
    """Router model."""

    id: int
    name: str
    user_id: int
    type: str
    aliases: list[str] | None = None
    load_balancing_strategy: str
    vector_size: int | None = None
    max_context_length: int | None = None
    cost_prompt_tokens: float
    cost_completion_tokens: float
    providers: int
    created: int
    updated: int


class FormattedRouter(BaseModel):
    """Formatted router for display."""

    id: int
    name: str
    user_id: int
    type: str
    aliases: list[str] | None
    load_balancing_strategy: str
    vector_size: int | None
    max_context_length: int | None
    cost_prompt_tokens: float
    cost_completion_tokens: float
    providers: int
    created: str
    updated: str
