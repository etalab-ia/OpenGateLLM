from abc import ABC, abstractmethod

from api.domain.key.entities import Key


class KeyAccessRepository(ABC):
    @abstractmethod
    async def validate_key(self, key: Key) -> tuple[int | None, int | None, str | None]:
        pass
