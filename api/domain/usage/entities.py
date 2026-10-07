from pydantic import field_validator

from api.domain import BaseModel, EntitiesPage, UtcDatetime


class EnvironmentalImpacts(BaseModel):
    kWh: float = 0.0
    kgCO2eq: float = 0.0

    @field_validator("kWh", "kgCO2eq")
    @classmethod
    def round_to_six_decimals(cls, value: float) -> float:
        return round(number=value, ndigits=6)


class PromptTokensDetails(BaseModel):
    cached_tokens: int = 0


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    prompt_tokens_details: PromptTokensDetails = PromptTokensDetails()
    cost: float = 0.0
    impacts: EnvironmentalImpacts = EnvironmentalImpacts()

    @field_validator("prompt_tokens_details", mode="before")
    @classmethod
    def coerce_null_prompt_tokens_details(cls, value: object) -> object:
        # vLLM and OpenAI send null when there are no cached tokens
        return PromptTokensDetails() if value is None else value

    @staticmethod
    def compute_request_cost(prompt_tokens: int, completion_tokens: int, cost_prompt_tokens: float, cost_completion_tokens: float) -> float:
        cost_tokens_scale = 1_000_000
        prompt_tokens_cost = prompt_tokens / cost_tokens_scale * cost_prompt_tokens
        completion_tokens_cost = completion_tokens / cost_tokens_scale * cost_completion_tokens
        return round(number=prompt_tokens_cost + completion_tokens_cost, ndigits=6)


class UsageRecord(BaseModel):
    request_id: str
    endpoint: str
    created: UtcDatetime
    user_id: int | None = None
    user_email: str | None = None
    key_id: int | None = None
    key_name: str | None = None
    router_id: int | None = None
    router_name: str | None = None
    provider_id: int | None = None
    provider_model_name: str | None = None
    usage: Usage | None = None
    status: int | None = None
    error: str | None = None
    latency: int | None = None
    ttft: int | None = None


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
