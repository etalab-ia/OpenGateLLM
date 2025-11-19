from contextvars import ContextVar

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.search import Searches, SearchRequest
from api.utils.context import global_context
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.exceptions import CollectionNotFoundException
from api.utils.hooks_decorator import hooks
from api.utils.variables import ENDPOINT__SEARCH, ROUTER__SEARCH

router = APIRouter(prefix="/v1", tags=[ROUTER__SEARCH.title()])


@router.post(path=ENDPOINT__SEARCH, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Searches)
@hooks
async def search(
    request: Request,
    body: SearchRequest,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: AsyncRedis = Depends(get_redis_client),
    model_registry: ModelRegistry = Depends(get_model_registry),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get relevant chunks from the collections and a query.
    """

    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    data = await global_context.document_manager.search_chunks(
        postgres_session=postgres_session,
        redis_client=redis_client,
        model_registry=model_registry,
        request_context=request_context,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        limit=body.limit,
        offset=body.offset,
        rff_k=body.rff_k,
        web_search=body.web_search,
    )
    usage = request_context.get().usage
    content = Searches(data=data, usage=usage)

    return JSONResponse(content=content.model_dump(), status_code=200)
