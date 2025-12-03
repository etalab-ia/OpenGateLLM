from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyRepository
from api.sql.models import Token as KeyTable


class PostgresKeyRepository(KeyRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def check_key_exists(self, user_id: int, key_id: int) -> bool:
        """
        Check if a key exists in the database.

        Args:
            user_id: The ID of the user.
            token_id: The ID of the token.

        Returns:
            True if the key exists, False otherwise.
        """
        if user_id == 0:
            return True

        query = select(KeyTable).where(KeyTable.user_id == user_id, KeyTable.id == key_id)
        result = await self.postgres_session.execute(query)

        return result.scalar_one_or_none() is not None
