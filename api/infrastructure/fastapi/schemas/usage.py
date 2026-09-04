from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from api.domain import BaseModel
from api.domain.usage.entities import UsageBucket
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


class UsageBucketResponse(BaseModel):
    object: Annotated[Literal["usage.bucket"], Field(default="usage.bucket", description="Type of the object.")]
    start_time: Annotated[int, Field(description="UTC start of the day bucket, as Unix timestamp.")]
    end_time: Annotated[int, Field(description="UTC exclusive end of the day bucket, as Unix timestamp.")]
    prompt_tokens: Annotated[int, Field(description="Sum of prompt tokens in the bucket.")]
    completion_tokens: Annotated[int, Field(description="Sum of completion tokens in the bucket.")]
    total_tokens: Annotated[int, Field(description="Sum of total tokens in the bucket.")]
    cost: Annotated[float, Field(description="Sum of request costs in the bucket.")]
    impacts: Annotated[EnvironmentalImpacts, Field(default_factory=EnvironmentalImpacts)]

    @model_validator(mode="before")
    @classmethod
    def from_usage_bucket(cls, data):
        if isinstance(data, UsageBucket):
            return {
                "object": "usage.bucket",
                "start_time": int(data.start_time.timestamp()),
                "end_time": int(data.end_time.timestamp()),
                "prompt_tokens": data.prompt_tokens,
                "completion_tokens": data.completion_tokens,
                "total_tokens": data.total_tokens,
                "cost": data.cost,
                "impacts": data.impacts,
            }
        return data


class UsagesResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of the object.")]
    total: Annotated[int, Field(description="Total number of usage buckets.")]
    offset: Annotated[int, Field(description="Offset of the usage buckets list.")]
    limit: Annotated[int, Field(description="Limit of the usage buckets list.")]
    data: Annotated[list[UsageBucketResponse], Field(description="List of daily usage buckets.")]
