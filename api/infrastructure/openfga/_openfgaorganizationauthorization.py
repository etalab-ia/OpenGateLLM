from api.domain.authorization.entities import AuthorizationObject, OrganizationRelation, PlatformRelation, RelationTuple
from api.domain.organization import OrganizationAuthorization
from api.infrastructure.openfga import OpenFgaAuthorizationClient


class OpenFgaOrganizationAuthorization(OrganizationAuthorization):
    def __init__(self, openfga_client: OpenFgaAuthorizationClient):
        self.openfga_client = openfga_client

    async def can_create_organization(self, user_id: int) -> bool:
        user_subject = AuthorizationObject.user(user_id)
        platform_object = AuthorizationObject.platform()

        res = await self.openfga_client.check(subject=user_subject, relation=PlatformRelation.CAN_CREATE_ORGANIZATION, object=platform_object)

        return res

    async def attach_organization_to_platform(self, organization_id: int) -> None:
        platform_subject = AuthorizationObject.platform()
        organization_object = AuthorizationObject.organization(organization_id)

        relation_tuple = RelationTuple(subject=platform_subject, relation=OrganizationRelation.PLATFORM, object=organization_object)

        await self.openfga_client.write_relation(relation_tuple)
