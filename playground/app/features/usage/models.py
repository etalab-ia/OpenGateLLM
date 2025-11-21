from pydantic import BaseModel


class UsageItem(BaseModel):
    created: int
    endpoint: str | None
    model: str | None
    key: str | None
    method: str | None
    status: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    latency: int | None
    ttft: int | None
    kwh_min: float | None
    kwh_max: float | None
    kgco2eq_min: float | None
    kgco2eq_max: float | None
