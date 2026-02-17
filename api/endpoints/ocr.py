from contextvars import ContextVar

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.core.models import RequestContent
from api.schemas.exception import HTTPExceptionModel
from api.schemas.ocr import OCR, CreateOCR
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.exceptions import (
    ModelIsTooBusyException,
    ModelNotFoundException,
    WrongModelTypeException,
)
from api.utils.hooks_decorator import hooks
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.OCR.upper()])


@hooks
@router.post(
    path=EndpointRoute.OCR,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses={
        ModelNotFoundException().status_code: {"model": HTTPExceptionModel, "description": ModelNotFoundException().detail},
        WrongModelTypeException().status_code: {"model": HTTPExceptionModel, "description": WrongModelTypeException().detail},
        ModelIsTooBusyException().status_code: {"model": HTTPExceptionModel, "description": ModelIsTooBusyException().detail},
    },
    response_model=OCR,
)
async def ocr(
    request: Request,
    body: CreateOCR,
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Extracts text from files using OCR.
    """
    model_provider = await model_registry.get_model_provider(
        model=body.model,
        endpoint=EndpointRoute.OCR,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )
    response = await model_provider.forward_request(
        request_content=RequestContent(method="POST", endpoint=EndpointRoute.OCR, json=body.model_dump(), model=body.model),
        redis_client=redis_client,
    )

    return JSONResponse(content=OCR(**response.json()).model_dump(), status_code=response.status_code)
