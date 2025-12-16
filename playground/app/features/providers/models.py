from app.shared.models.entities import Entity


class Provider(Entity):
    """Provider model."""

    id: int | None = None
    router: str | None = None
    user: str | None = None
    type: str | None = None
    url: str | None = None
    key: str | None = None
    timeout: int = 300
    model_name: str | None = None
    model_carbon_footprint_zone: str = "WOR"
    model_carbon_footprint_total_params: int | None = 0
    model_carbon_footprint_active_params: int | None = 0
    qos_metric: str | None = None
    qos_limit: float | None = None
    max_context_length: int | None = None
    vector_size: int | None = None
    created: str | None = None
