from fastapi import APIRouter, Depends, Path, Request, Security
from fastapi.responses import JSONResponse

from api.dependencies import get_models_use_case
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.schemas.models import Model, Models
from api.schemas.exception import HTTPExceptionModel
from api.use_cases.models import GetModelsUseCase
from api.use_cases.models._getmodelsusecase import ModelNotFound, Success
from api.utils.exceptions import ModelNotFoundException, RouterNotFoundException
from api.utils.variables import ENDPOINT__MODELS, ROUTER__MODELS

router = APIRouter(prefix="/v1", tags=[ROUTER__MODELS.title()])


@router.get(
    path=ENDPOINT__MODELS + "/{model:path}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Model,
    responses={ModelNotFoundException().status_code: {"model": HTTPExceptionModel, "description": {ModelNotFoundException().detail}}},
)
async def get_model(
    request: Request,
    model: str = Path(description="The name of the model to get."),
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case),
) -> ModelNotFoundException | RouterNotFoundException | JSONResponse:
    """
    Get a model by name and provide basic information.
    """
    result = await get_models_use_case.execute(name=model)

    match result:
        case Success(models):
            models = [Model(**model.model_dump()) for model in models]
            model = models[0]
            return JSONResponse(content=model.model_dump(), status_code=200)
        case ModelNotFound():
            raise ModelNotFoundException()


@router.get(
    path=ENDPOINT__MODELS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Models,
    responses={ModelNotFoundException().status_code: {"model": HTTPExceptionModel, "description": {ModelNotFoundException().detail}}},
)
async def get_models(
    request: Request,
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case),
) -> JSONResponse:
    """
    Lists the currently available models and provides basic information.
    """
    result = await get_models_use_case.execute(name=None)
    match result:
        case Success(models):
            models = [Model(**model.model_dump()) for model in models]
            return JSONResponse(content=Models(data=models).model_dump(), status_code=200)
