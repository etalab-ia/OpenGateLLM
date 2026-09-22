from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from tiktoken import Encoding

if TYPE_CHECKING:
    from langfuse import Langfuse
    from redis.asyncio import ConnectionPool
    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    redis_pool: ConnectionPool | None = None
    postgres_session_factory: async_sessionmaker | None = None
    autocommit_postgres_session_factory: async_sessionmaker | None = None
    postgres_engine: AsyncEngine | None = None
    langfuse: Langfuse | None = None
    tokenizer: Encoding | None = None


global_context: GlobalContext = GlobalContext.model_construct()
