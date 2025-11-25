from app.shared.models.entities import Entity


class Router(Entity):
    """Router model."""

    id: int | None = None
    name: str | None = None
    user: str | None = None
    type: str | None = None
    aliases: str | None = None
    load_balancing_strategy: str | None = None
    vector_size: int | None = None
    max_context_length: int | None = None
    cost_prompt_tokens: float | None = None
    cost_completion_tokens: float | None = None
    providers: int | None = None
    created: str | None = None
    updated: str | None = None
