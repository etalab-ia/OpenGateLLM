from pydantic import BaseModel


class Usage(BaseModel):
    start_time: int = 0
    end_time: int = 0
    date: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    kwh: float = 0.0
    kgco2eq: float | None = None
    endpoint: str | None = None
    model: str | None = None
    key: str | None = None
    created: str | None = None
    id: int | None = None


UsageBucket = Usage
