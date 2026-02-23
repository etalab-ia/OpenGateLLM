from fastapi import HTTPException
from pydantic import BaseModel

from api.infrastructure.fastapi.endpoints.exceptions import (
    InvalidAPIKeyException,
    InvalidAuthenticationSchemeException,
)


class HTTPExceptionModel(BaseModel):
    status_code: int
    detail: str
    headers: dict[str, str] | None = None


def get_documentation_responses(exceptions: list[HTTPException]):
    """
    Generate a dictionary of responses for a list of HTTP exceptions in Redoc and Swagger documentation.
    """
    exceptions.extend([InvalidAuthenticationSchemeException, InvalidAPIKeyException])
    responses = {}
    for exception in exceptions:
        if exception.status_code not in responses:
            responses[exception.status_code] = {"model": HTTPExceptionModel, "description": exception.detail}
        else:
            responses[exception.status_code]["description"] += f"<br>{exception.detail}"

    return responses
