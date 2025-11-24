from pydantic import BaseModel


class Router(BaseModel):
    """Router model."""

    id: int
    name: str
    user: str
    type: str
    aliases: list[str] | None = None
    load_balancing_strategy: str
    vector_size: int | None
    max_context_length: int | None
    cost_prompt_tokens: float
    cost_completion_tokens: float
    providers: int
    created: str
    updated: str
