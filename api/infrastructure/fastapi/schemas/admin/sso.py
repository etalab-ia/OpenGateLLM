from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from api.domain import BaseModel
from api.domain.auth.entities import SsoAccessRuleType, SsoPolicy


class SsoPolicyEmailRuleBody(BaseModel):
    type: Annotated[Literal[SsoAccessRuleType.EMAIL], Field(description="The SSO policy rule type.")]
    value: Annotated[str , StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(description="Matches email addresses ending with this value.")]  # fmt: off


class SsoPolicyOrganizationRuleBody(BaseModel):
    type: Annotated[Literal[SsoAccessRuleType.ORGANIZATION], Field(description="The SSO policy rule type.")]
    value: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(default=None, description="Matches organization name exactly. If not provided, users without organization will be added to the organization specified by the organization_id.")]  # fmt: off
    organization_id: Annotated[int, Field(description="The organization ID.")]


class SsoPolicyRoleRuleBody(BaseModel):
    type: Annotated[Literal[SsoAccessRuleType.ROLE], Field(description="The SSO policy rule type.")]
    value: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=254), Field(default=None, description="Matches OIDC group name exactly. If not provided, users without OIDC group will be added to the role specified by the role_id.")]  # fmt: off
    role_id: Annotated[int, Field(description="The role ID.")]


class SsoPolicyEmailRuleResponse(SsoPolicyEmailRuleBody):
    id: Annotated[int, Field(description="The SSO policy rule ID.")]
    object: Annotated[Literal["ssoPolicyEmailRule"], Field(default="ssoPolicyEmailRule", description="Matches email addresses ending with this value.")]  # fmt: off
    created: Annotated[int, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(description="Time of last update, as Unix timestamp.")]


class SsoPolicyOrganizationRuleResponse(SsoPolicyOrganizationRuleBody):
    id: Annotated[int, Field(description="The SSO policy rule ID.")]
    object: Annotated[Literal["ssoPolicyOrganizationRule"], Field(default="ssoPolicyOrganizationRule", description="Matches organization name.")]
    created: Annotated[int, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(description="Time of last update, as Unix timestamp.")]


class SsoPolicyRoleRuleResponse(SsoPolicyRoleRuleBody):
    id: Annotated[int, Field(description="The SSO policy rule ID.")]
    object: Annotated[Literal["ssoPolicyRoleRule"], Field(default="ssoPolicyRoleRule", description="Type of object.")]
    created: Annotated[int, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[int, Field(description="Time of last update, as Unix timestamp.")]


type SsoPolicyRuleBody = SsoPolicyEmailRuleBody | SsoPolicyOrganizationRuleBody | SsoPolicyRoleRuleBody


class SsoPolicyRulesBody(BaseModel):
    rules: list[SsoPolicyRuleBody] = Field(default_factory=list, description="List of SSO policy rules.")


type SsoPolicyRuleResponse = SsoPolicyEmailRuleResponse | SsoPolicyOrganizationRuleResponse | SsoPolicyRoleRuleResponse


class SsoPolicyResponse(BaseModel):
    object: Annotated[Literal["list"], Field(default="list", description="Type of object.")]
    data: list[SsoPolicyRuleResponse] = Field(default_factory=list, description="List of SSO policy rules.")

    @model_validator(mode="before")
    @classmethod
    def from_policy(cls, data):
        if isinstance(data, SsoPolicy):
            return {
                "data": [
                    {
                        **rule.model_dump(),
                        "created": int(rule.created.timestamp()),
                        "updated": int(rule.updated.timestamp()),
                    }
                    for rule in data.rules
                ],
            }
        return data
