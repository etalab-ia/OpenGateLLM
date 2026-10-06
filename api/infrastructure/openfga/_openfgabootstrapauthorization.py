from api.domain.authorization.entities import AuthorizationObject, PlatformRelation, RelationTuple
from api.domain.user import BootstrapAuthorization
from api.infrastructure.openfga._openfgaauthorizationclient import OpenFgaAuthorizationClient


class OpenFgaBootstrapAuthorization(BootstrapAuthorization):
    def __init__(self, openfga_client: OpenFgaAuthorizationClient):
        self.openfga_client = openfga_client

    async def attach_bootstrap_admin_to_platform(self, user_id: int) -> None:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        if await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.ADMIN, object=platform_object):
            return

        relation_tuple = RelationTuple(subject=user_subject, relation=PlatformRelation.ADMIN, object=platform_object)
        await self.openfga_client.write_relation(relation_tuple)
