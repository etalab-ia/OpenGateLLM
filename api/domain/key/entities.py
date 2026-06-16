from datetime import UTC, datetime

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
        expires = claims.get("expires")
        if isinstance(expires, str):
            expires = datetime.fromisoformat(expires)

        return cls(
            id=claims["token_id"],
            name="",
            user_id=claims["user_id"],
            expires=expires,
            created=datetime.now(UTC),
        )

    def is_valid(self, expected_key: "Key") -> bool:
        return self.id == expected_key.id and self.user_id == expected_key.user_id and self.expires == expected_key.expires
