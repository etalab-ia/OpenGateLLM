from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.search import Searches, SearchRequest
from api.sql.session import get_db_session
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_model_registry, get_redis_client
from api.utils.exceptions import CollectionNotFoundException
from api.utils.variables import ENDPOINT__SEARCH, ROUTER__SEARCH

router = APIRouter(prefix="/v1", tags=[ROUTER__SEARCH.title()])


@router.post(path=ENDPOINT__SEARCH, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Searches)
async def search(
    request: Request,
    body: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
    redis_client: AsyncRedis = Depends(get_redis_client),
    model_registry: ModelRegistry = Depends(get_model_registry),
) -> JSONResponse:
    """
    Get relevant chunks from the collections and a query.
    """

    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    data = await global_context.document_manager.search_chunks(
        session=session,
        redis_client=redis_client,
        model_registry=model_registry,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        limit=body.limit,
        offset=body.offset,
        rff_k=body.rff_k,
        user_info=request_context.get().user_info,
        web_search=body.web_search,
    )
    usage = request_context.get().usage
    content = Searches(data=data, usage=usage)

    return JSONResponse(content=content.model_dump(), status_code=200)
