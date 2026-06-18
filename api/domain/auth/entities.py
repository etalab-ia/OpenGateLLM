from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SsoAccessRuleType(StrEnum):
    EMAIL = "email"
    ORGANIZATION = "organization"
    ROLE = "role"


class SsoAccessRule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    type: SsoAccessRuleType
    value: str


class SsoRoleMapping(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    organization_name: str
    oidc_role_name: str
    role_id: int


class SsoPolicy(BaseModel):
    allowed_emails: list[str] = Field(default_factory=list)
    allowed_organizations: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    role_mappings: list[SsoRoleMapping] = Field(default_factory=list)
