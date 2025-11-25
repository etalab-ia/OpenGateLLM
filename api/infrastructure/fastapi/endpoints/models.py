from fastapi import APIRouter, Depends, Path, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_models_use_case, get_postgres_session
from api.domain.access import AccessController
from api.schemas.exception import HTTPExceptionModel
from api.schemas.models import Model, Models
from api.use_cases.models import GetModelsUseCase
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
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get a model by name and provide basic information.
    """
    models = await get_models_use_case.execute(name=model)
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
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Lists the currently available models and provides basic information.
    """
    models = await get_models_use_case.execute(name=None)

    return JSONResponse(content=Models(data=models).model_dump(), status_code=200)
