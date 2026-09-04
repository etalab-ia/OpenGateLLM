from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from api.domain import BaseModel
from api.domain.usage.entities import UsageRecord
from api.infrastructure.fastapi.schemas import UnixTimestamp
from api.utils.variables import EndpointRoute


class EndpointUsage(StrEnum):
    AUDIO_TRANSCRIPTIONS = f"/v1{EndpointRoute.AUDIO_TRANSCRIPTIONS}"
    CHAT_COMPLETIONS = f"/v1{EndpointRoute.CHAT_COMPLETIONS}"
    EMBEDDINGS = f"/v1{EndpointRoute.EMBEDDINGS}"
    OCR = f"/v1{EndpointRoute.OCR}"
    RERANK = f"/v1{EndpointRoute.RERANK}"
    SEARCH = "/v1/search"


class EnvironmentalImpacts(BaseModel):
    kWh: Annotated[float, Field(default=0.0, description="Energy consumption in kWh.")]
    kgCO2eq: Annotated[float, Field(default=0.0, description="Carbon footprint in kgCO2eq (global warming potential).")]


class UsageDetail(BaseModel):
    prompt_tokens: Annotated[int | None, Field(default=None, description="Number of prompt tokens (e.g. input tokens).")]
    completion_tokens: Annotated[int | None, Field(default=None, description="Number of completion tokens (e.g. output tokens).")]
    total_tokens: Annotated[int | None, Field(default=None, description="Total number of tokens (e.g. input and output tokens).")]
    cost: Annotated[float | None, Field(default=None, description="Total cost of the request.")]
    impacts: Annotated[EnvironmentalImpacts, Field(default_factory=EnvironmentalImpacts)]


class UsageResponse(BaseModel):
    object: Annotated[Literal["usage"], Field(default="usage", description="Type of the object.")]
    model: Annotated[str | None, Field(default=None, description="Model used for the request.")]
    key: Annotated[str | None, Field(default=None, description="Key used for the request.")]
    endpoint: Annotated[str | None, Field(default=None, description="Endpoint used for the request.")]
    usage: Annotated[UsageDetail, Field(default_factory=UsageDetail)]
    created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]

    @model_validator(mode="before")
    @classmethod
    def nest_usage_counters(cls, data):
        if isinstance(data, UsageRecord):
            return data.model_copy(update={"usage": data})
        return data


class UsagesResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of the object.")]
    total: Annotated[int, Field(description="Total number of usages.")]
    offset: Annotated[int, Field(description="Offset of the usages list.")]
    limit: Annotated[int, Field(description="Limit of the usages list.")]
    data: Annotated[list[UsageResponse], Field(description="List of usages.")]
