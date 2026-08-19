from typing import Annotated, Any

from pydantic import Field, StringConstraints

from api.domain import BaseModel
from api.infrastructure.fastapi.schemas.admin.keys import KeyResponse


class AuthLoginBody(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(description="The user email.")]
    password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72), Field(description="The user password.")]


class AuthLoginResponse(KeyResponse):
    pass


class AuthSsoLoginBody(BaseModel):
    sub: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Subject identifier from the OIDC id_token.")]
    iss: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Issuer identifier from the OIDC id_token.")]
    exp: Annotated[int, Field(description="Expiration timestamp (seconds since epoch) from the OIDC id_token.")]
    claims: Annotated[dict[str, Any], Field(default_factory=dict, description="OIDC claims from the identity provider access token /userinfo endpoint.")]  # fmt: off
