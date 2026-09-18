from http import HTTPMethod

from api.domain import BaseModel, EntitiesPage, UtcDatetime


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


class UsageBucket(BaseModel):
    start_time: UtcDatetime
    end_time: UtcDatetime
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    requests: int = 0
    impacts: EnvironmentalImpacts = EnvironmentalImpacts()


UsageBucketPage = EntitiesPage["UsageBucket"]


class UsageRecord(BaseModel):
    id: int | None = None
    created: UtcDatetime

    # request
    endpoint: str
    method: HTTPMethod | None = None

    # user identifiers
    user_id: int | None = None
    user_email: str | None = None
    key_id: int | None = None
    key_name: str | None = None

    # model identifiers
    router_id: int | None = None
    router_name: str | None = None
    provider_id: int | None = None
    provider_model_name: str | None = None

    # response
    status: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    kwh: float | None = None
    kgco2eq: float | None = None
    latency: int | None = None
    ttft: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)
