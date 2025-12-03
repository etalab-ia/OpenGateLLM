from abc import ABC, abstractmethod


class KeyRepository(ABC):
    @abstractmethod
    async def check_key_exists(self, user_id: int, key_id: int) -> bool:
        pass
