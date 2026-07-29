from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends
import redis.asyncio as redis
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.key import KeyEncoder, KeyRepository
from api.infrastructure.jwt import JwtKeyEncoder
from api.infrastructure.postgres import PostgresAuthenticatedUserQuery, PostgresKeyRepository
from api.utils.configuration import configuration
from api.utils.context import global_context


# databases
async def get_postgres_session() -> AsyncGenerator[AsyncSession]:
    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        try:
            yield postgres_session
            if postgres_session.in_transaction():
                await postgres_session.commit()
        except Exception:
            if postgres_session.in_transaction():
                await postgres_session.rollback()
            raise


async def get_redis_client() -> AsyncGenerator[Redis, Any]:
    client = redis.Redis(connection_pool=global_context.redis_pool)
    yield client
    await client.aclose()


# queries
def _authenticated_user_query(session: AsyncSession = Depends(get_postgres_session)) -> PostgresAuthenticatedUserQuery:
    return PostgresAuthenticatedUserQuery(postgres_session=session)


# helpers
def _key_encoder() -> KeyEncoder:
    return JwtKeyEncoder(secret_key=configuration.settings.auth_secret_key)


# repositories
def _key_repository(key_encoder: KeyEncoder = Depends(_key_encoder), session: AsyncSession = Depends(get_postgres_session)) -> KeyRepository:
    return PostgresKeyRepository(key_encoder=key_encoder, postgres_session=session)
