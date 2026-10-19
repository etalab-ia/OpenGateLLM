from abc import ABC, abstractmethod

from api.domain.authorization.entities import AuthorizationObject, AuthorizationRelation, RelationTuple


class AuthorizationClient(ABC):
    @abstractmethod
    async def check(self, subject: AuthorizationObject, relation: AuthorizationRelation, object: AuthorizationObject) -> bool:
        pass

    @abstractmethod
    async def write_relation(self, relation_tuple: RelationTuple) -> None:
        pass

    @abstractmethod
    async def delete_relation(self, relation_tuple: RelationTuple) -> None:
        pass
