from enum import Enum
from typing import Annotated, Literal

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


class CarbonFootprintUsage(BaseModel):
    kWh: Annotated[float | None, Field(default=None, description="Carbon footprint in kWh.")]
    kgCO2eq: Annotated[float | None, Field(default=None, description="Carbon footprint in kgCO2eq (global warming potential).")]


class UsageDetail(BaseModel):
    prompt_tokens: Annotated[int | None, Field(default=None, description="Number of prompt tokens (e.g. input tokens).")]
    completion_tokens: Annotated[int | None, Field(default=None, description="Number of completion tokens (e.g. output tokens).")]
    total_tokens: Annotated[int | None, Field(default=None, description="Total number of tokens (e.g. input and output tokens).")]
    cost: Annotated[float | None, Field(default=None, description="Total cost of the request.")]
    carbon: Annotated[CarbonFootprintUsage, Field(default_factory=CarbonFootprintUsage)]
    metrics: Annotated[MetricsUsage, Field(default_factory=MetricsUsage)]


class Usage(BaseModel):
    object: Annotated[Literal["me.usage"], Field(default="me.usage", description="Object type.")]
    model: Annotated[str | None, Field(default=None, description="Model used for the request.")]
    key: Annotated[str | None, Field(default=None, description="Key used for the request.")]
    endpoint: Annotated[str | None, Field(default=None, description="Endpoint used for the request.")]
    method: Annotated[str | None, Field(default=None, description="Method used for the request.")]
    status: Annotated[int | None, Field(default=None, description="Status code of the response.")]
    usage: Annotated[UsageDetail, Field(default_factory=UsageDetail)]
    created: Annotated[int, Field(description="Timestamp in seconds")]


class Usages(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Object type.")]
    data: Annotated[list[Usage], Field(description="List of usages.")]
