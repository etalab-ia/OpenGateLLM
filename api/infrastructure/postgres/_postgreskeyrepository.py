from pydantic import FutureDatetime
from sqlalchemy import asc, delete, desc, func, insert, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain import SortField, SortOrder
from api.domain.key import KeyEncoder, KeyRepository
from api.domain.key.entities import Key, KeyPage, KeyStatus
from api.domain.key.errors import KeyAlreadyExistsError, KeyNotFoundError
from api.domain.user.errors import UserNotFoundError
from api.infrastructure.postgres._pagination import fetch_page_with_total
from api.sql.models import Token as KeyTable


class PostgresKeyRepository(KeyRepository):
    def __init__(self, key_encoder: KeyEncoder, postgres_session: AsyncSession):
        self.key_encoder = key_encoder
        self.postgres_session = postgres_session

    @staticmethod
    def _row_to_key(row, *, value: str | None = None) -> Key:
        return Key(
            id=row.id,
            name=row.name,
            user_id=row.user_id,
            value=value if value is not None else row.token,
            expires=row.expires,
            created=row.created,
        )

    async def get_key_by_id(self, key_id: int) -> Key | KeyNotFoundError:
        query = select(KeyTable).where(KeyTable.id == key_id)
        result = await self.postgres_session.execute(query)

        row = result.scalar_one_or_none()
        if row is None:
            return KeyNotFoundError(id=key_id)

        return self._row_to_key(row)

    async def get_keys_page(
        self,
        user_id: int | None = None,
        limit: int = 10,
        offset: int = 0,
        sort_by: SortField = SortField.ID,
        sort_order: SortOrder = SortOrder.ASC,
        status: KeyStatus | None = None,
    ) -> KeyPage:
        sort_column = {SortField.ID: KeyTable.id, SortField.NAME: KeyTable.name, SortField.CREATED: KeyTable.created}[sort_by]
        order_fn = asc if sort_order == SortOrder.ASC else desc

        filters = []
        if user_id is not None:
            filters.append(KeyTable.user_id == user_id)
        if status == KeyStatus.ACTIVE:
            filters.append(or_(KeyTable.expires.is_(None), KeyTable.expires >= func.now()))
        elif status == KeyStatus.EXPIRED:
            filters.append(KeyTable.expires.isnot(None))
            filters.append(KeyTable.expires < func.now())

        key_query = select(KeyTable, func.count().over().label("total")).where(*filters).order_by(order_fn(sort_column)).offset(offset).limit(limit)
        count_query = select(func.count()).select_from(KeyTable).where(*filters)
        rows, total = await fetch_page_with_total(self.postgres_session, key_query, count_query)
        keys = [self._row_to_key(row[0]) for row in rows]
        return KeyPage(total=total, data=keys)

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

        return self._row_to_key(row, value=value)

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

        return self._row_to_key(row, value=value)

    async def delete_key(self, key_id: int, user_id: int | None = None) -> Key | KeyNotFoundError:
        filters = [KeyTable.id == key_id]
        if user_id is not None:
            filters.append(KeyTable.user_id == user_id)

        result = await self.postgres_session.execute(delete(KeyTable).where(*filters).returning(KeyTable))
        row = result.scalar_one_or_none()
        if row is None:
            return KeyNotFoundError(id=key_id)

        return self._row_to_key(row)
