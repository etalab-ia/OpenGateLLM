from app.shared.models.entities import Entity


class Provider(Entity):
    """Provider model."""

    id: int | None = None
    router: str | None = None
    user: str | None = None
    type: str | None = None
    url: str | None = None
    key: str | None = None
    timeout: int | None = None
    model_name: str | None = None
    model_carbon_footprint_zone: str = "WOR"
    model_carbon_footprint_total_params: int | None = None
    model_carbon_footprint_active_params: int | None = None
    qos_metric: str | None = None
    qos_limit: float | None = None
    created: str | None = None
