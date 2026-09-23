from enum import StrEnum

from pydantic import ConfigDict

from api.domain import BaseModel

PLATFORM_ID = "api"


class AuthorizationObjectType(StrEnum):
    PLATFORM = "platform"
    ORGANIZATION = "organization"
    USER = "user"


class PlatformRelation(StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    CAN_CREATE_ORGANIZATION = "can_create_organization"


class OrganizationRelation(StrEnum):
    PLATFORM = "platform"
    MEMBER = "member"
    CAN_READ = "can_read"
    CAN_UPDATE = "can_update"
    CAN_DELETE = "can_delete"
    CAN_ADD_MEMBER = "can_add_member"
    CAN_REMOVE_MEMBER = "can_remove_member"


type AuthorizationRelation = PlatformRelation | OrganizationRelation


class AuthorizationObject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: AuthorizationObjectType
    id: str

    @classmethod
    def platform(cls) -> "AuthorizationObject":
        return cls(type=AuthorizationObjectType.PLATFORM, id=PLATFORM_ID)

    @classmethod
    def organization(cls, organization_id: int) -> "AuthorizationObject":
        return cls(type=AuthorizationObjectType.ORGANIZATION, id=str(organization_id))

    @classmethod
    def user(cls, user_id: int) -> "AuthorizationObject":
        return cls(type=AuthorizationObjectType.USER, id=str(user_id))

    def __str__(self) -> str:
        return f"{self.type.value}:{self.id}"


class RelationTuple(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: AuthorizationObject
    relation: AuthorizationRelation
    object: AuthorizationObject

    @classmethod
    def organization_platform(cls, organization_id: int) -> "RelationTuple":
        return cls(
            subject=AuthorizationObject.platform(),
            relation=OrganizationRelation.PLATFORM,
            object=AuthorizationObject.organization(organization_id),
        )
