from abc import ABC, abstractmethod

from pydantic import FutureDatetime

from api.domain import SortField, SortOrder
from api.domain.key.entities import Key, KeyPage
from api.domain.key.errors import KeyAlreadyExistsError, KeyNotFoundError
from api.domain.user.errors import UserNotFoundError


class KeyRepository(ABC):
    @abstractmethod
    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        pass

    @abstractmethod
    async def get_keys_page(
        self,
        user_id: int | None = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: SortField = SortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
        exclude_expired: bool = True,
    ) -> KeyPage:
        pass

    @abstractmethod
    async def create_key(self, user_id: int, name: str, expire: FutureDatetime | None) -> Key | KeyAlreadyExistsError | UserNotFoundError:
        pass

    @abstractmethod
    async def upsert_key(self, user_id: int, name: str, expire: FutureDatetime | None) -> Key | UserNotFoundError:
        pass

    @abstractmethod
    async def delete_key(self, key_id: int) -> Key | KeyNotFoundError:
        pass
