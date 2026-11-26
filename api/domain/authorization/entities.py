from enum import StrEnum

from pydantic import ConfigDict

from api.domain import BaseModel

PLATFORM_ID = "api"


class AuthorizationObjectType(StrEnum):
    PLATFORM = "platform"
    ORGANIZATION = "organization"
    USER = "user"


class PlatformRelation(StrEnum):
    ADMIN = "admin"

    CAN_CREATE_ORGANIZATION = "can_create_organization"
    CAN_READ_ORGANIZATION = "can_read_organization"

    CAN_CREATE_USER = "can_create_user"
    CAN_READ_USER = "can_read_user"
    CAN_UPDATE_USER = "can_update_user"
    CAN_DELETE_USER = "can_delete_user"

    CAN_CREATE_ROUTER = "can_create_router"
    CAN_READ_ROUTER = "can_read_router"
    CAN_UPDATE_ROUTER = "can_update_router"
    CAN_DELETE_ROUTER = "can_delete_router"

    CAN_CREATE_ROLE = "can_create_role"


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
