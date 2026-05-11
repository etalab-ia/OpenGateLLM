from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.domain.key.errors import KeyNotFoundError
from api.sql.models import Token as KeyTable


class PostgresKeyRepository(KeyRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_key_expiration(self, user_id: int, key_id: int) -> int | KeyNotFoundError:
        query = select(cast(func.extract("epoch", KeyTable.expires), Integer).label("expires")).where(
            KeyTable.user_id == user_id, KeyTable.id == key_id
        )
        result = await self.postgres_session.execute(query)

        row = result.one_or_none()
        if row is None:
            return KeyNotFoundError()

        return row.expires
