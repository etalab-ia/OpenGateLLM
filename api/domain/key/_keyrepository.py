from abc import ABC, abstractmethod

from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError


class KeyRepository(ABC):
    @abstractmethod
    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        pass
