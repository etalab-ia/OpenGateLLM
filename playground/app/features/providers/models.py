from app.shared.models.entities import Entity


class Provider(Entity):
    """Provider model."""

    id: int
    router: str
    user: str
    type: str
    url: str
    key: str
    timeout: int
    model_name: str
    model_carbon_footprint_zone: str
    model_carbon_footprint_total_params: int | None
    model_carbon_footprint_active_params: int | None
    qos_metric: str | None
    qos_limit: float | None
    created: str
