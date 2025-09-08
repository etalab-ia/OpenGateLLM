from pydantic import Field, constr

from api.schemas import BaseModel


class Login(BaseModel):
    email: constr(strip_whitespace=True, min_length=1) = Field(description="The user email.")
    password: constr(strip_whitespace=True, min_length=1) = Field(description="The user password.")


class LoginResponse(BaseModel):
    id: int = Field(description="The Playground API key ID.")
    key: str = Field(description="The playground API key.")
