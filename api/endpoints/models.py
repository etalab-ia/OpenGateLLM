from contextvars import ContextVar

from fastapi import APIRouter, Depends, Path, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.exception import HTTPExceptionModel
from api.schemas.models import Model, Models
from api.utils.dependencies import get_model_registry, get_postgres_session, get_request_context
from api.utils.exceptions import ModelNotFoundException
from api.utils.variables import ENDPOINT__MODELS, ROUTER__MODELS

router = APIRouter(prefix="/v1", tags=[ROUTER__MODELS.title()])


@router.get(
    path=ENDPOINT__MODELS + "/{model:path}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Model,
    responses={ModelNotFoundException().status_code: {"model": HTTPExceptionModel, "description": {ModelNotFoundException().detail}}},
)
async def get_model(
    request: Request,
    model: str = Path(description="The name of the model to get."),
    model_registry: ModelRegistry = Depends(get_model_registry),
    session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get a model by name and provide basic information.
    """
    models = await model_registry.get_models(name=model, user_info=request_context.get().user_info, session=session)
    model = models[0]

    return JSONResponse(content=model.model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__MODELS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Models,
    responses={ModelNotFoundException().status_code: {"model": HTTPExceptionModel, "description": {ModelNotFoundException().detail}}},
)
async def get_models(
    request: Request,
    model_registry: ModelRegistry = Depends(get_model_registry),
    session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Lists the currently available models and provides basic information.
    """
    models = await model_registry.get_models(name=None, user_info=request_context.get().user_info, session=session)

    return JSONResponse(content=Models(data=models).model_dump(), status_code=200)
