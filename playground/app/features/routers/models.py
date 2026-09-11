from app.shared.models.entities import Entity


class Router(Entity):
    """Router model."""

    id: int | None = None
    name: str | None = None
    user: str | None = None
    type: str | None = None
    aliases: str | None = None
    load_balancing_strategy: str | None = None
    qos_enable: bool = False
    qos_retry: int | None = None
    qos_metric: str | None = None
    qos_health_threshold_start: float = 0.9
    qos_health_threshold_end: float = 1.1
    cost_prompt_tokens: float | None = None
    cost_completion_tokens: float | None = None
    providers: int | None = None
    created: str | None = None
    updated: str | None = None
