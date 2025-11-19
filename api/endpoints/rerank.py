from contextvars import ContextVar

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.rerank import RerankRequest, Reranks
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.hooks_decorator import hooks
from api.utils.variables import ENDPOINT__RERANK, ROUTER__RERANK

router = APIRouter(prefix="/v1", tags=[ROUTER__RERANK.title()])


@router.post(path=ENDPOINT__RERANK, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Reranks)
@hooks
async def rerank(
    request: Request,
    body: RerankRequest,
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """
    model_provider = await model_registry.get_model_provider(
        model=body.model,
        endpoint=ENDPOINT__RERANK,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )
    response = await model_provider.forward_request(method="POST", json=body.model_dump(), endpoint=ENDPOINT__RERANK, redis_client=redis_client)

    return JSONResponse(content=Reranks(**response.json()).model_dump(), status_code=response.status_code)
