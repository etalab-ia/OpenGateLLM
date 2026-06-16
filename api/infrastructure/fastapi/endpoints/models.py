from fastapi import APIRouter, Depends, Path, Security
from fastapi.responses import JSONResponse

from api.dependencies import get_model_use_case_factory, get_models_use_case_factory, get_request_context
from api.domain.model.errors import ModelNotFoundError
from api.domain.user.errors import UserExpiredError
from api.infrastructure.fastapi.access import decode_api_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import AccountExpiredHTTPException, ModelNotFoundHTTPException
from api.infrastructure.fastapi.schemas.models import Model, ModelsResponse
from api.use_cases.models import GetModelCommand, GetModelsCommand, GetModelsUseCase, GetModelsUseCaseSucess, GetModelUseCase, GetModelUseCaseSucess
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.MODELS.title()])


@router.get(
    path=EndpointRoute.MODELS,
    dependencies=[Security(dependency=decode_api_key)],
    status_code=200,
    response_model=ModelsResponse,
    responses=get_documentation_responses([]),
)
async def get_models(
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case_factory),
    request_context: RequestContext = Depends(get_request_context),
) -> ModelNotFoundHTTPException | JSONResponse:
    """
    Lists the currently available models and provides basic information.
    """
    command = GetModelsCommand(user_id=request_context.get().user_id)
    result = await get_models_use_case.execute(command=command)

    match result:
        case GetModelsUseCaseSucess(models):
            return JSONResponse(content=ModelsResponse.model_validate({"data": models}, from_attributes=True).model_dump(), status_code=200)
        case UserExpiredError():
            raise AccountExpiredHTTPException()


@router.get(
    path=EndpointRoute.MODELS + "/{model:path}",
    dependencies=[Security(dependency=decode_api_key)],
    status_code=200,
    response_model=Model,
    responses=get_documentation_responses([ModelNotFoundHTTPException]),
)
async def get_model(
    model: str = Path(description="The name of the model to get."),
    get_model_use_case: GetModelUseCase = Depends(get_model_use_case_factory),
    request_context: RequestContext = Depends(get_request_context),
) -> JSONResponse:
    """
    Get a model by name and provide basic information.
    """
    command = GetModelCommand(user_id=request_context.get().user_id, name=model)
    result = await get_model_use_case.execute(command=command)

    match result:
        case GetModelUseCaseSucess(model):
            return JSONResponse(content=Model.model_validate(model, from_attributes=True).model_dump(), status_code=200)
        case ModelNotFoundError(name):
            raise ModelNotFoundHTTPException(name=name)
        case UserExpiredError():
            raise AccountExpiredHTTPException()
