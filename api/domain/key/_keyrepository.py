from abc import ABC, abstractmethod

from api.domain.key.errors import KeyNotFoundError


class KeyRepository(ABC):
    @abstractmethod
    async def get_key_expiration(self, user_id: int, key_id: int) -> int | KeyNotFoundError:
        pass
