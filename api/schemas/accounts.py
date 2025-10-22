from typing import Literal

from pydantic import Field

from api.schemas import BaseModel


class AccountUsage(BaseModel):
    """Schema for individual account usage record."""

    id: int
    datetime: int = Field(description="Timestamp in seconds")
    duration: int | None = None
    time_to_first_token: int | None = None
    user_id: int | None = None
    token_id: int | None = None
    endpoint: str
    method: str | None = None
    model: str | None = None
    request_model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: float | None = None
    total_tokens: int | None = None
    cost: float | None = None
    status: int | None = None
    kwh_min: float | None = None
    kwh_max: float | None = None
    kgco2eq_min: float | None = None
    kgco2eq_max: float | None = None


class AccountUsageResponse(BaseModel):
    """Schema for list of account usage records."""

    object: Literal["list"] = "list"
    data: list[AccountUsage]
    total: int = Field(description="Total number of records")
    total_requests: int = Field(description="Total number of requests made")
    total_albert_coins: float | None = Field(description="Total Albert coins earned")
    total_tokens: int | None = Field(description="Total tokens used")
    total_co2: float | None = Field(description="Total CO2 emissions in grams")

    # Pagination metadata
    page: int = Field(description="Current page number (1-based)")
    limit: int = Field(description="Number of records per page")
    total_pages: int = Field(description="Total number of pages")
    has_more: bool = Field(description="Whether there are more records available")
