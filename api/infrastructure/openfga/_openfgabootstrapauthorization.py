import logging

from openfga_sdk.exceptions import OpenApiException

from api.domain.authorization.entities import AuthorizationObject, PlatformRelation, RelationTuple
from api.domain.user import BootstrapAuthorization
from api.infrastructure.openfga._openfgaauthorizationclient import OpenFgaAuthorizationClient

logger = logging.getLogger(__name__)


class OpenFgaBootstrapAuthorization(BootstrapAuthorization):
    def __init__(self, openfga_client: OpenFgaAuthorizationClient):
        self.openfga_client = openfga_client

    async def attach_bootstrap_admin_to_platform(self, user_id: int) -> None:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        if await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.ADMIN, object=platform_object):
            return

        relation_tuple = RelationTuple(subject=user_subject, relation=PlatformRelation.ADMIN, object=platform_object)
        try:
            await self.openfga_client.write_relation(relation_tuple)
            logger.info(f"OpenFGA platform admin relation granted to the bootstrap admin (user ID: {user_id}).")
        except OpenApiException:
            if not await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.ADMIN, object=platform_object):
                raise
            logger.info(f"OpenFGA platform admin relation already granted to the bootstrap admin (user ID: {user_id}), skipping...")
