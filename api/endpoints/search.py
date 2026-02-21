from contextvars import ContextVar

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.search import CreateSearch, Searches
from api.utils.context import global_context
from api.utils.dependencies import (
    get_elasticsearch_client,
    get_elasticsearch_vector_store,
    get_model_registry,
    get_postgres_session,
    get_redis_client,
    get_request_context,
)
from api.utils.hooks_decorator import hooks
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.SEARCH.title()])


@router.post(path=EndpointRoute.SEARCH, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Searches)
@hooks
async def search(
    request: Request,
    body: CreateSearch,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: AsyncRedis = Depends(get_redis_client),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    model_registry: ModelRegistry = Depends(get_model_registry),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get relevant chunks from the collections and a query.
    """
    data = await global_context.document_manager.search_chunks(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        redis_client=redis_client,
        model_registry=model_registry,
        request_context=request_context,
        collection_ids=body.collection_ids,
        document_ids=body.document_ids,
        metadata_filters=body.metadata_filters,
        query=body.query,
        method=body.method,
        limit=body.limit,
        offset=body.offset,
        rff_k=body.rff_k,
        score_threshold=body.score_threshold,
    )
    usage = request_context.get().usage
    content = Searches(data=data, usage=usage)

    return JSONResponse(content=content.model_dump(mode="json"), status_code=200)
