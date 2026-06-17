from abc import ABC, abstractmethod

from pydantic import FutureDatetime


class KeyEncoder(ABC):
    KEY_PREFIX: str = "sk-"
    ENCODING_ALGORITHM: str = "HS256"

    @abstractmethod
    def encode_token(self, user_id: int, key_id: int, expires: FutureDatetime | None = None) -> str:
        pass

    @abstractmethod
    def decode(self, key_value: str) -> dict:
        pass
