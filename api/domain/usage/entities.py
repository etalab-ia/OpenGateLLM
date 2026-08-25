from datetime import datetime

from api.domain import BaseModel, EntitiesPage


class EnvironmentalImpacts(BaseModel):
    kWh: float = 0.0
    kgCO2eq: float = 0.0


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    impacts: EnvironmentalImpacts = EnvironmentalImpacts()

    @staticmethod
    def compute_request_cost(prompt_tokens: int, completion_tokens: int, cost_prompt_tokens: float, cost_completion_tokens: float) -> float:
        cost_tokens_scale = 1_000_000
        prompt_tokens_cost = prompt_tokens / cost_tokens_scale * cost_prompt_tokens
        completion_tokens_cost = completion_tokens / cost_tokens_scale * cost_completion_tokens
        return round(number=prompt_tokens_cost + completion_tokens_cost, ndigits=6)


class UsageRecord(BaseModel):
    model: str | None
    key: str | None
    endpoint: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost: float | None
    impacts: EnvironmentalImpacts
    created: datetime


UsagePage = EntitiesPage["UsageRecord"]
