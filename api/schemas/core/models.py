from enum import Enum
from http import HTTPMethod

from pydantic import BaseModel, Field

from api.utils import variables

Endpoint = Enum("Endpoint", {name.upper(): value for name, value in vars(variables).items() if name.startswith("ENDPOINT__")}, type=str)


class RequestContent(BaseModel):
    method: HTTPMethod
    model: str = Field(description="The called model name.")
    endpoint: Endpoint = Field(description="The source endpoint (at the user side) of the request.")
    json: dict = Field(default={}, description="The JSON body to use for the request.")
    form: dict = Field(default={}, description="The form-encoded data to use for the request.")
    files: dict = Field(default={}, description="The files to use for the request.")
    additional_data: dict = Field(default={}, description="The additional data to add to the response.")

    # @TODO: add a build method to build the request content from a request (after clean architecture refactor)


class Metric(str, Enum):
    TTFT = "ttft"  # time to first token
    LATENCY = "latency"  # requests latency
    INFLIGHT = "inflight"  # requests concurrency
    PERFORMANCE = "performance"  # custom performance metric


# TEI
class TruncationDirection(Enum):
    left = "left"
    right = "right"


class TEICreateRerank(BaseModel):
    query: str = Field(..., examples=["What is Deep Learning?"])
    raw_scores: bool = Field(False, examples=[False])
    return_text: bool = Field(False, examples=[False])
    texts: list[str] = Field(..., examples=[["Deep Learning is ..."]])
    truncate: bool | None = Field(False, examples=[False])
    truncation_direction: TruncationDirection = "right"
