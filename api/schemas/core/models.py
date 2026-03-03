from enum import StrEnum
from http import HTTPMethod
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from api.utils.variables import EndpointRoute


class RequestContent(BaseModel):
    method: HTTPMethod
    model: str | None = Field(default=None, description="The called model name. If None, the model name, request ID and usage are not added to the response.")  # fmt: off
    endpoint: Annotated[EndpointRoute, Field(description="The source endpoint (at the user side) of the request.")]
    body: dict = Field(default={}, description="The JSON body to use for the request.")
    form: dict = Field(default={}, description="The form-encoded data to use for the request.")
    files: dict = Field(default={}, description="The files to use for the request.")
    additional_data: dict = Field(default={}, description="The additional data to add to the response.")

    # @TODO: add a build method to build the request content from a request (after clean architecture refactor)
    # @TODO: build body with model_fields_set to exclude unset fields


class Metric(StrEnum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric
