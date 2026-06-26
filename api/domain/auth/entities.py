from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class SsoAccessRuleType(StrEnum):
    EMAIL = "email"
    ORGANIZATION = "organization"
    ROLE = "role"


class NewSsoPolicyEmailRule(BaseModel):
    type: Literal[SsoAccessRuleType.EMAIL]
    value: str


class NewSsoPolicyOrganizationRule(BaseModel):
    type: Literal[SsoAccessRuleType.ORGANIZATION]
    value: str | None = None
    organization_id: int


class NewSsoPolicyRoleRule(BaseModel):
    type: Literal[SsoAccessRuleType.ROLE]
    value: str | None = None
    role_id: int


type NewSsoPolicyRule = NewSsoPolicyEmailRule | NewSsoPolicyOrganizationRule | NewSsoPolicyRoleRule


class NewSsoPolicy(BaseModel):
    rules: list[NewSsoPolicyRule] = Field(default_factory=list)


class SsoPolicyRuleBase(BaseModel):
    id: int
    type: SsoAccessRuleType
    created: datetime
    updated: datetime


class SsoPolicyEmailRule(SsoPolicyRuleBase):
    type: Literal[SsoAccessRuleType.EMAIL]
    value: str


class SsoPolicyOrganizationRule(SsoPolicyRuleBase):
    type: Literal[SsoAccessRuleType.ORGANIZATION]
    value: str | None = None
    organization_id: int


class SsoPolicyRoleRule(SsoPolicyRuleBase):
    type: Literal[SsoAccessRuleType.ROLE]
    value: str | None = None
    role_id: int


type SsoPolicyRule = SsoPolicyEmailRule | SsoPolicyOrganizationRule | SsoPolicyRoleRule


class SsoPolicy(BaseModel):
    rules: list[SsoPolicyRule] = Field(default_factory=list)

    def is_allowed(self, email: str, organization: str | None, roles: list[str]) -> bool:
        checks: list[bool] = []
        allowed_emails = [rule.value for rule in self.rules if rule.type == SsoAccessRuleType.EMAIL]
        allowed_organizations = [rule.value for rule in self.rules if rule.type == SsoAccessRuleType.ORGANIZATION and rule.value is not None]
        allowed_roles = [rule.value for rule in self.rules if rule.type == SsoAccessRuleType.ROLE and rule.value is not None]

        if allowed_roles:
            checks.append(any(role in allowed_roles for role in roles))

        if allowed_emails:
            checks.append(any(email.endswith(allowed_email) for allowed_email in allowed_emails))

        if allowed_organizations:
            checks.append(organization is not None and organization in allowed_organizations)

        return True if not checks else any(checks)

    def get_matching_organization_rule(self, organization: str | None) -> SsoPolicyOrganizationRule | None:
        for rule in self.rules:
            if rule.type != SsoAccessRuleType.ORGANIZATION:
                continue
            if organization is None and rule.value is None:  # default organization rule
                return rule
            if organization is not None and organization == rule.value:
                return rule

    def get_matching_role_rule(self, roles: list[str]) -> SsoPolicyRoleRule | None:
        for rule in self.rules:
            if rule.type != SsoAccessRuleType.ROLE:
                continue
            if not roles and rule.value is None:  # default role rule
                return rule
            if roles and rule.value in roles:
                return rule
