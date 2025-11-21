from enum import Enum
from typing import Literal

from pydantic import Field

from api.schemas import BaseModel


class EndpointUsage(Enum):
    AUDIO_TRANSCRIPTIONS = "/v1/audio/transcriptions"
    CHAT_COMPLETIONS = "/v1/chat/completions"
    EMBEDDINGS = "/v1/embeddings"
    OCR = "/v1/ocr"
    RERANK = "/v1/rerank"
    SEARCH = "/v1/search"


class MetricsUsage(BaseModel):
    latency: int | None = None
    ttft: int | None = None


class CarbonFootprintUsageKWh(BaseModel):
    min: float | None = Field(default=None, description="Minimum carbon footprint in kWh.")
    max: float | None = Field(default=None, description="Maximum carbon footprint in kWh.")


class CarbonFootprintUsageKgCO2eq(BaseModel):
    min: float | None = Field(default=None, description="Minimum carbon footprint in kgCO2eq (global warming potential).")
    max: float | None = Field(default=None, description="Maximum carbon footprint in kgCO2eq (global warming potential).")


class CarbonFootprintUsage(BaseModel):
    kWh: CarbonFootprintUsageKWh = Field(default_factory=CarbonFootprintUsageKWh)
    kgCO2eq: CarbonFootprintUsageKgCO2eq = Field(default_factory=CarbonFootprintUsageKgCO2eq)


class UsageDetail(BaseModel):
    prompt_tokens: int | None = Field(default=None, description="Number of prompt tokens (e.g. input tokens).")
    completion_tokens: int | None = Field(default=None, description="Number of completion tokens (e.g. output tokens).")
    total_tokens: int | None = Field(default=None, description="Total number of tokens (e.g. input and output tokens).")
    cost: float | None = Field(default=None, description="Total cost of the request.")
    carbon: CarbonFootprintUsage = Field(default_factory=CarbonFootprintUsage)
    metrics: MetricsUsage = Field(default_factory=MetricsUsage)


class Usage(BaseModel):
    object: Literal["me.usage"] = "me.usage"
    model: str | None = Field(default=None, description="Model used for the request.")
    key: str | None = Field(default=None, description="Key used for the request.")
    endpoint: str | None = Field(default=None, description="Endpoint used for the request.")
    method: str | None = Field(default=None, description="Method used for the request.")
    status: int | None = Field(default=None, description="Status code of the response.")
    usage: UsageDetail = Field(default_factory=UsageDetail)
    created: int = Field(description="Timestamp in seconds")


class Usages(BaseModel):
    object: Literal["list"] = "list"
    data: list[Usage]
