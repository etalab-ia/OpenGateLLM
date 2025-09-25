from pydantic import Field
from typing import Optional

from api.schemas import BaseModel


class CarbonFootprintUsageKWh(BaseModel):
    min: float | None = Field(default=None, description="Minimum carbon footprint in kWh.")
    max: float | None = Field(default=None, description="Maximum carbon footprint in kWh.")


class CarbonFootprintUsageKgCO2eq(BaseModel):
    min: float | None = Field(default=None, description="Minimum carbon footprint in kgCO2eq (global warming potential).")
    max: float | None = Field(default=None, description="Maximum carbon footprint in kgCO2eq (global warming potential).")


class CarbonFootprintUsage(BaseModel):
    kWh: CarbonFootprintUsageKWh = Field(default_factory=CarbonFootprintUsageKWh)
    kgCO2eq: CarbonFootprintUsageKgCO2eq = Field(default_factory=CarbonFootprintUsageKgCO2eq)


class TaskMetrics(BaseModel):
    strategy: str = Field(default="", description="Strategy used to choose a client.")
    policy: Optional[str] = Field(default=None, description="QoS policy used to decide whether or not the message should be requeued.")
    priority: int = Field(default=0, description="Priority of the user who made the request.")
    requeue_count: int = Field(default=0, description="Number of times the celery task had to be retried before succeeding.")
    get_client_duration: int = Field(default=0, description="Total duration (in milliseconds) of the celery task, including retries.")
    performance_score: Optional[float] = Field(default=None, description="Performance score like time to first token, if relevant.")


class Observability(BaseModel):
    client_url: str = Field(default="", description="Address at which the request has been forwarded.")
    max_parallel_requests: Optional[int] = Field(
        default=None, description="Maximum number of requests that the chosen server is able to handle at the same time."
    )
    current_parallel_requests: int = Field(default=0, description="Number of requests currently handled by the chosen server.")
    task_metrics: TaskMetrics = Field(default_factory=TaskMetrics)


class BaseUsage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Number of prompt tokens (e.g. input tokens).")
    completion_tokens: int = Field(default=0, description="Number of completion tokens (e.g. output tokens).")
    total_tokens: int = Field(default=0, description="Total number of tokens (e.g. input and output tokens).")
    cost: float = Field(default=0.0, description="Total cost of the request.")
    carbon: CarbonFootprintUsage = Field(default_factory=CarbonFootprintUsage)
    observability: Observability = Field(default_factory=Observability)


class Detail(BaseModel):
    id: str
    model: str
    usage: BaseUsage = Field(default_factory=BaseUsage)


class Usage(BaseUsage):
    details: list[Detail] = []
