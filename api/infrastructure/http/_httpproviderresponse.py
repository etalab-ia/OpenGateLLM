from typing import Annotated

from pydantic import Field

from api.domain import BaseModel


class HttpProviderResponse(BaseModel):
    data: Annotated[dict | list | None, Field(default=None, description="The JSON data to use for the response.")]
    text: Annotated[str | None, Field(default=None, description="The text data to use for the response.")]
