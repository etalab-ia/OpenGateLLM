from app.shared.models.entities import Entity


class Usage(Entity):
    endpoint: str | None = None
    model: str | None = None
    key: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    kgco2eq_min: float | None = None
    kgco2eq_max: float | None = None
    created: str | None = None
