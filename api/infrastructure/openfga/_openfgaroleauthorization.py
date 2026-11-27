from api.domain.authorization.entities import AuthorizationObject, PlatformRelation
from api.domain.role import RoleAuthorization
from api.infrastructure.openfga._openfgaauthorizationclient import OpenFgaAuthorizationClient


class OpenFgaRoleAuthorization(RoleAuthorization):
    def __init__(self, openfga_client: OpenFgaAuthorizationClient):
        self.openfga_client = openfga_client

    async def can_create_role(self, user_id: int) -> bool:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        return await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.CAN_CREATE_ROLE, object=platform_object)

    async def can_delete_role(self, user_id: int, role_id: int) -> bool:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        return await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.CAN_DELETE_ROLE, object=platform_object)
