from datetime import datetime

from pydantic import Field

from api.schemas import BaseModel


class Metric(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    time_to_first_token_us: int | None = None
    latency_ms: int | None = None
    model_name: str = ""
    provider_url: str = ""
