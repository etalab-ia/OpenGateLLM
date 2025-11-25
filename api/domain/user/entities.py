from pydantic import BaseModel, Field


class User(BaseModel):
    id: int = Field(description="The user ID.")
    email: str = Field(description="The user email.")
    name: str | None = Field(default=None, description="The user name.")
    sub: str | None = Field(default=None, description="The user subject identifier. Null when using email/password auth.")
    iss: str | None = Field(default=None, description="The user issuer identifier. Null when using email/password auth.")
    role: int = Field(description="The user role ID.")
    organization: int | None = Field(default=None, description="The user organization ID.")
    budget: float | None = Field(default=None, description="The user budget. If None, the user has unlimited budget.")
    expires: int | None = Field(default=None, description="The user expiration timestamp. If None, the user will never expire.")
    created: int = Field(description="The user creation timestamp.")
    updated: int = Field(description="The user update timestamp.")
    priority: int = Field(description="The user priority (higher = higher priority).")
