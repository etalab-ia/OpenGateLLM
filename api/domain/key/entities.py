from datetime import UTC, datetime
from enum import StrEnum

from api.domain import BaseModel, EntitiesPage, UtcDatetime


class KeyStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"


class Key(BaseModel):
    id: int
    name: str
    user_id: int
    value: str
    expires: UtcDatetime | None
    created: UtcDatetime
    status: KeyStatus | None = None

    @classmethod
    def build_from_claims(cls, claims: dict):
        return cls(
            id=claims["token_id"],
            name="",
            value="",
            user_id=claims["user_id"],
            expires=claims.get("expires", claims.get("expires_at")),  # legacy support for expires_at: remove after 2027-08-10
            created=0,
        )

    def is_valid(self, expected_key: "Key") -> bool:
        now_ts = int(datetime.now(tz=UTC).timestamp())
        expected_expires_ts = self._expires_timestamp(expected_key.expires)

        if expected_expires_ts is not None and expected_expires_ts < now_ts:
            return False

        # some legacy keys has expiration date unsync with database: after 2027-08-10, we can add a check to ensure the expiration date is sync with the database.
        # decoded_expires == self._expires_timestamp(expected_key.expires)
        return self.user_id == expected_key.user_id

    @staticmethod
    def _expires_timestamp(expires: datetime | None) -> int | None:
        if expires is None:
            return None
        return int(expires.timestamp())

    @staticmethod
    def compute_status(expires: UtcDatetime | None) -> KeyStatus:
        if expires is not None and expires < datetime.now(tz=UTC):
            return KeyStatus.EXPIRED
        return KeyStatus.ACTIVE

    def with_computed_status(self) -> "Key":
        return self.model_copy(update={"status": self.compute_status(self.expires)})


KeyPage = EntitiesPage["Key"]
