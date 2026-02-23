from fastapi import APIRouter, Depends, Path, Request, Security
from fastapi.responses import JSONResponse

from api.dependencies import get_models_use_case
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import ModelNotFoundHTTPException
from api.infrastructure.fastapi.schemas.models import Model, Models
from api.use_cases.models import GetModelsUseCase
from api.use_cases.models._getmodelsusecase import ModelNotFound, Success
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.MODELS.title()])


@router.get(
    path=EndpointRoute.MODELS + "/{model:path}",
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Model,
    responses=get_documentation_responses([ModelNotFoundHTTPException]),
)
async def get_model(
    request: Request,
    model: str = Path(description="The name of the model to get."),
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case),
) -> ModelNotFoundHTTPException | JSONResponse:
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
            raise ModelNotFoundHTTPException()


@router.get(
    path=EndpointRoute.MODELS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    response_model=Models,
    responses=get_documentation_responses([ModelNotFoundHTTPException]),
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
