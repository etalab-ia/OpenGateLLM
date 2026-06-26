from typing import Annotated

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas.admin.keys import CreateKeyResponse


class AuthLoginBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(description="The user email.")
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] = Field(description="The user password.")


class AuthLoginResponse(CreateKeyResponse):
    pass


class AuthSsoLoginBody(BaseModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(default=None, description="The user name.")  # fmt: off
    organization: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(default=None, description="The organization name. If organization not found, a new organization will be created.")  # fmt: off
    roles: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)]] = Field(default_factory=list, description="OIDC role claim values from the identity provider.")  # fmt: off
    sub: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(default=None, description="The OIDC subject identifier.")  # fmt: off
    iss: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(default=None, description="The OIDC issuer identifier.")  # fmt: off
    expires: int | None = Field(default=None, ge=1, description="Unix timestamp when the OIDC token expires. Used as the playground API key expiration.")  # fmt: off
