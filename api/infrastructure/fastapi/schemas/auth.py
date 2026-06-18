from typing import Annotated

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas.admin.keys import CreateKeyResponse


class AuthLoginBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(description="The user email.")
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] = Field(description="The user password.")


class AuthLoginResponse(CreateKeyResponse):
    pass


class AuthOidcLoginBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(description="The user email.")
    id_token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(description="The ID token for SSO login.")  # fmt: off
