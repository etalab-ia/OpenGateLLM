from datetime import UTC, datetime

from api.domain import BaseModel


class KeyClaims(BaseModel):
    user_id: int
    key_id: int


class Key(BaseModel):
    id: int
    name: str
    user_id: int
    value: str
    expires: datetime | None
    created: datetime

    @classmethod
    def build_from_claims(cls, claims: dict):
        return cls(id=claims["token_id"], name="", value="", user_id=claims["user_id"], expires=claims["expires"], created=0)

    def is_valid(self, expected_key: "Key") -> bool:
        decoded_expires = self._expires_timestamp(self.expires)
        if decoded_expires is not None and decoded_expires < int(datetime.now(tz=UTC).timestamp()):
            return False

        return self.user_id == expected_key.user_id and decoded_expires == self._expires_timestamp(expected_key.expires)

    @staticmethod
    def _expires_timestamp(expires: datetime | None) -> int | None:
        if expires is None:
            return None
        return int(expires.timestamp())
