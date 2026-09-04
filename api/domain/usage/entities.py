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
    impacts: EnvironmentalImpacts = EnvironmentalImpacts()


UsageBucketPage = EntitiesPage["UsageBucket"]
