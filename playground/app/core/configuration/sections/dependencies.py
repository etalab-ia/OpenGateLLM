from typing import Annotated

from pydantic import Field, StringConstraints

from app.core.configuration._interpolation import ConfigBaseModel
from app.core.configuration._validationerrors import custom_validation_error


@custom_validation_error
class RedisDependency(ConfigBaseModel):
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^redis://"), Field(..., description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])]  # fmt: off


@custom_validation_error
class Dependencies(ConfigBaseModel):
    redis: Annotated[RedisDependency | None, Field(default=None, description="Redis is a required dependency for the API to store rate limiting counters and inflight gauges. It is an optional dependency for the Playground to use as stage manage (see [Reflex documentation](https://reflex.dev/docs/api-reference/config/)).")]  # fmt: off
