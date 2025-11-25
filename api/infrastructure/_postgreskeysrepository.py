from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyAccessRepository
from api.domain.key.entities import Key
from api.sql.models import Token as KeyTable
from api.utils.context import request_context
from api.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException


class PostgresKeyAccessRepository(KeyAccessRepository):
    def __init__(self, postgres_session: AsyncSession, master_key: str):
        self.postgres_session = postgres_session
        self.master_key = master_key

    async def check_key_exists(self, user_id: int, token_id: int) -> bool:
        query = select(KeyTable).where(KeyTable.user_id == user_id, KeyTable.id == token_id)
        result = await self.postgres_session.execute(query)
        return result.scalar_one_or_none() is not None

    async def __call__(
        self,
        request: Request,
        api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
        postgres_session: AsyncSession = Depends(get_postgres_session),
    ) -> tuple[int | None, int | None, str | None]:
        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        claims = Key(value=api_key.credentials).decode(master_key=self.master_key)
        user_id = claims.get("user_id")
        token_id = claims.get("token_id")
        expires = claims.get("expires")

        if not await self.check_key_exists(user_id=user_id, token_id=token_id):
            raise InvalidAPIKeyException()

        if not user_id or not token_id or not expires:
            raise InvalidAPIKeyException()

        context = request_context.get()
        context.user_id = user_id
        context.token_id = token_id

        return user_id, token_id, expires
