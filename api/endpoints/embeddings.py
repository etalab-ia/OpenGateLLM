from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.embeddings import Embeddings, EmbeddingsRequest
from api.utils.context import request_context
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client
from api.utils.hooks_decorator import hooks
from api.utils.variables import ENDPOINT__EMBEDDINGS, ROUTER__EMBEDDINGS

router = APIRouter(prefix="/v1", tags=[ROUTER__EMBEDDINGS.title()])


@router.post(path=ENDPOINT__EMBEDDINGS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Embeddings)
@hooks
async def embeddings(
    request: Request,
    body: EmbeddingsRequest,
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Creates an embedding vector representing the input text.
    """

    model_provider = await model_registry.get_model_provider(
        model=body.model,
        endpoint=ENDPOINT__EMBEDDINGS,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )
    response = await model_provider.forward_request(method="POST", json=body.model_dump(), endpoint=ENDPOINT__EMBEDDINGS, redis_client=redis_client)

    return JSONResponse(content=Embeddings(**response.json()).model_dump(), status_code=response.status_code)
