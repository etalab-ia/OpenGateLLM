from jose import jwt
from pydantic import FutureDatetime
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.sql.models import Token as KeyTable


class PostgresKeyRepository(KeyRepository):
    def __init__(self, postgres_session: AsyncSession, secret_key: str):
        self.postgres_session = postgres_session
        self.secret_key = secret_key

    def _encode_token(self, user_id: int, token_id: int, expires: FutureDatetime | None = None) -> str:
        expires = int(expires.timestamp()) if expires is not None else None
        return KeyRepository.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires": expires},
            key=self.secret_key,
            algorithm="HS256",
        )

    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        query = select(KeyTable).where(KeyTable.id == key_id)
        result = await self.postgres_session.execute(query)

        row = result.scalar_one_or_none()
        if row is None:
            return KeyNotFoundError(id=key_id)

        return Key(id=row.id, name=row.name, user_id=row.user_id, value=row.token, expires=row.expires, created=row.created)

    async def create_key(self, user_id: int, name: str, expire: FutureDatetime | None) -> Key | UserNotFoundError:
        try:
            result = await self.postgres_session.execute(insert(KeyTable).values(user_id=user_id, name=name, expires=expire).returning(KeyTable))
            row = result.scalar_one()
        except IntegrityError as e:
            if "token_user_id_fkey" in str(e.orig):
                return UserNotFoundError(id=user_id)
            raise

        value = self._encode_token(user_id=user_id, token_id=row.id, expires=expire)
        registered_value = f"{value[:8]}...{value[-8:]}"

        await self.postgres_session.execute(update(KeyTable).values(token=registered_value).where(KeyTable.id == row.id))

        return Key(id=row.id, name=row.name, user_id=row.user_id, value=value, expires=row.expires, created=row.created)
