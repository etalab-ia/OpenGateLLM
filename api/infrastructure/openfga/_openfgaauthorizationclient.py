from openfga_sdk.client import OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple

from api.domain.authorization import AuthorizationClient
from api.domain.authorization.entities import AuthorizationObject, AuthorizationRelation, RelationTuple


class OpenFgaAuthorizationClient(AuthorizationClient):
    def __init__(self, client: OpenFgaClient):
        self.client = client

    async def check(self, subject: AuthorizationObject, relation: AuthorizationRelation, object: AuthorizationObject) -> bool:
        request = ClientCheckRequest(user=str(subject), relation=str(relation), object=str(object))
        response = await self.client.check(body=request)

        return response.allowed

    async def write_relation(self, relation_tuple: RelationTuple) -> None:
        await self.client.write_tuples(body=[self._to_client_tuple(relation_tuple)])

    async def delete_relation(self, relation_tuple: RelationTuple) -> None:
        await self.client.delete_tuples(body=[self._to_client_tuple(relation_tuple)])

    @staticmethod
    def _to_client_tuple(relation_tuple: RelationTuple) -> ClientTuple:
        return ClientTuple(user=str(relation_tuple.subject), relation=str(relation_tuple.relation), object=str(relation_tuple.object))
