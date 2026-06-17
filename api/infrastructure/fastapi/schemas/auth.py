from typing import Annotated

from pydantic import Field, StringConstraints

from api.infrastructure.fastapi.schemas.admin.keys import CreateKeyResponse
from api.schemas import BaseModel


class AuthLoginBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(description="The user email.")
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] = Field(description="The user password.")


class AuthLoginResponse(CreateKeyResponse):
    pass
