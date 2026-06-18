from pydantic import FutureDatetime
from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyEncoder, KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyAlreadyExistsError, KeyNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.sql.models import Token as KeyTable


class PostgresKeyRepository(KeyRepository):
    def __init__(self, key_encoder: KeyEncoder, postgres_session: AsyncSession):
        self.key_encoder = key_encoder
        self.postgres_session = postgres_session

    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        query = select(KeyTable).where(KeyTable.id == key_id)
        result = await self.postgres_session.execute(query)

        row = result.scalar_one_or_none()
        if row is None:
            return KeyNotFoundError(id=key_id)

        return Key(id=row.id, name=row.name, user_id=row.user_id, value=row.token, expires=row.expires, created=row.created)

    async def create_key(self, user_id: int, name: str, expire: FutureDatetime | None) -> Key | KeyAlreadyExistsError | UserNotFoundError:
        try:
            result = await self.postgres_session.execute(insert(KeyTable).values(user_id=user_id, name=name, expires=expire).returning(KeyTable))
            row = result.scalar_one()
        except IntegrityError as e:
            if "token_user_id_fkey" in str(e.orig):
                return UserNotFoundError(id=user_id)
            if "unique_token_name_per_user" in str(e.orig):
                return KeyAlreadyExistsError(name=name)
            raise

        value = self.key_encoder.encode_token(user_id=user_id, key_id=row.id, expires=expire)
        registered_value = f"{value[:8]}...{value[-8:]}"

        await self.postgres_session.execute(update(KeyTable).values(token=registered_value).where(KeyTable.id == row.id))

        return Key(id=row.id, name=row.name, user_id=row.user_id, value=value, expires=row.expires, created=row.created)

    async def upsert_key(self, user_id: int, name: str, expire: FutureDatetime | None) -> Key | UserNotFoundError:
        try:
            result = await self.postgres_session.execute(
                pg_insert(KeyTable)
                .values(user_id=user_id, name=name, expires=expire)
                .on_conflict_do_update(
                    constraint="unique_token_name_per_user",
                    set_={"expires": expire},
                )
                .returning(KeyTable)
            )
            row = result.scalar_one()
        except IntegrityError as e:
            if "token_user_id_fkey" in str(e.orig):
                return UserNotFoundError(id=user_id)
            raise

        value = self.key_encoder.encode_token(user_id=user_id, key_id=row.id, expires=expire)
        registered_value = f"{value[:8]}...{value[-8:]}"

        await self.postgres_session.execute(update(KeyTable).values(token=registered_value).where(KeyTable.id == row.id))

        return Key(id=row.id, name=row.name, user_id=row.user_id, value=value, expires=row.expires, created=row.created)
