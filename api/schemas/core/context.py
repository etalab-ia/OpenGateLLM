from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from api.schemas.me.info import UserInfo
from api.schemas.usage import Usage

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch
    from redis.asyncio import ConnectionPool
    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

    from api.clients.parser._baseparserclient import BaseParserClient
    from api.helpers._documentmanager import DocumentManager
    from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
    from api.helpers._identityaccessmanager import IdentityAccessManager
    from api.helpers._limiter import Limiter
    from api.helpers._parsermanager import ParserManager
    from api.helpers._usagemanager import UsageManager
    from api.helpers._usagetokenizer import UsageTokenizer
    from api.helpers.models import ModelRegistry


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    document_manager: DocumentManager | None = None
    identity_access_manager: IdentityAccessManager | None = None
    limiter: Limiter | None = None
    usage_manager: UsageManager | None = None
    model_registry: ModelRegistry | None = None
    parser_manager: ParserManager | None = None
    elasticsearch_vector_store: ElasticsearchVectorStore | None = None
    tokenizer: UsageTokenizer | None = None
    parser: BaseParserClient | None = None

    elasticsearch_client: AsyncElasticsearch | None = None
    redis_pool: ConnectionPool | None = None
    postgres_session_factory: async_sessionmaker | None = None
    postgres_engine: AsyncEngine | None = None


class RequestContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    # request identifiers
    id: str | None = None
    method: str | None = None
    endpoint: str | None = None

    # request context
    user_info: UserInfo | None = None
    key_id: int | None = None
    key_name: str | None = None
    router_id: int | None = None
    provider_id: int | None = None

    # request body
    router_name: str | None = None
    provider_model_name: str | None = None

    # response
    usage: Usage | None = None
    ttft: int | None = None
    latency: int | None = None
