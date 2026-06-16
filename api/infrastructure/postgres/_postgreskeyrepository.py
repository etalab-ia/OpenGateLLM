from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.domain.key.entities import Key
from api.domain.key.errors import KeyNotFoundError
from api.sql.models import Token as KeyTable


class PostgresKeyRepository(KeyRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        query = select(KeyTable).where(KeyTable.id == key_id)
        result = await self.postgres_session.execute(query)

        row = result.scalar_one_or_none()
        if row is None:
            return KeyNotFoundError()

        return Key(id=row.id, name=row.name, user_id=row.user_id, expires=row.expires, created=row.created)
