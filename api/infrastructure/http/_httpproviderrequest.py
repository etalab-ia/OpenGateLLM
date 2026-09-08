from http import HTTPMethod
from typing import Annotated

from pydantic import Field

from api.domain import BaseModel
from api.domain.provider.entities import BasicAuth


class HttpProviderRequest(BaseModel):
    method: Annotated[HTTPMethod, Field(description="The HTTP method to build the request.")]
    url: Annotated[str, Field(description="The model API URL to build the request.")]
    auth: Annotated[BasicAuth | None, Field(default=None, description="The authentication to use for the request.")]
    body: Annotated[dict, Field(default={}, description="The JSON body to use for the request.")]
    form: Annotated[dict, Field(default={}, description="The form-encoded data to use for the request.")]
    files: Annotated[dict, Field(default={}, description="The files to use for the request.")]
