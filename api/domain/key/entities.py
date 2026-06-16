from datetime import datetime

from pydantic import BaseModel, FutureDatetime


class KeyClaims(BaseModel):
    user_id: int
    key_id: int


class Key(BaseModel):
    id: int
    name: str
    user_id: int
    expires: FutureDatetime | None = None
    created: datetime

    @classmethod
    def build_from_claims(cls, claims: dict):
        return cls(id=claims["token_id"], name="", user=claims["user_id"], expires=claims["expires"], created=0)

    def is_valid(self, expected_key: "Key") -> bool:
        return self.id == expected_key.id and self.user_id == expected_key.user_id and self.expires == expected_key.expires
