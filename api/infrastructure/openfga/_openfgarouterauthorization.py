from api.domain.authorization.entities import AuthorizationObject, PlatformRelation
from api.domain.router import RouterAuthorization
from api.infrastructure.openfga._openfgaauthorizationclient import OpenFgaAuthorizationClient


class OpenFgaRouterAuthorization(RouterAuthorization):
    def __init__(self, openfga_client: OpenFgaAuthorizationClient):
        self.openfga_client = openfga_client

    async def can_create_router(self, user_id: int) -> bool:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        res = await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.CAN_CREATE_ROUTER, object=platform_object)

        return res

    async def can_delete_router(self, user_id: int, router_id: int) -> bool:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        res = await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.CAN_DELETE_ROUTER, object=platform_object)

        return res

    async def can_update_router(self, user_id: int, router_id: int) -> bool:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        res = await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.CAN_UPDATE_ROUTER, object=platform_object)

        return res
