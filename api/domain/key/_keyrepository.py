from abc import ABC, abstractmethod

from pydantic import FutureDatetime

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.user.errors import UserNotFoundError


class KeyRepository(ABC):
    @abstractmethod
    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        pass

    @abstractmethod
    async def create_key(self, user_id: int, name: str, expire: FutureDatetime | None) -> Key | UserNotFoundError:
        pass
