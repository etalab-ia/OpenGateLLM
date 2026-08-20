import logging

from fastapi import APIRouter, Depends, Path, Security
from fastapi.responses import JSONResponse

from api.dependencies import get_models_use_case_factory, get_one_model_use_case_factory
from api.domain.model.errors import ModelNotFoundError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException, ModelNotFoundHTTPException
from api.infrastructure.fastapi.schemas.models import Model, ModelsResponse
from api.use_cases.models import (
    GetModelsCommand,
    GetModelsUseCase,
    GetModelsUseCaseSucess,
    GetOneModelCommand,
    GetOneModelUseCase,
    GetOneModelUseCaseSuccess,
)
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=[RouterName.MODELS.title()])


@router.get(
    path=EndpointRoute.MODELS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=ModelsResponse,
    responses=get_documentation_responses([]),
)
async def get_models(
    get_models_use_case: GetModelsUseCase = Depends(get_models_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> ModelNotFoundHTTPException | JSONResponse:
    """
    Lists the currently available models and provides basic information.
    """
    command = GetModelsCommand(authenticated_user=authenticated_user)
    try:
        result = await get_models_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_models use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetModelsUseCaseSucess(models):
            return JSONResponse(content=ModelsResponse.model_validate({"data": models}, from_attributes=True).model_dump(), status_code=200)


@router.get(
    path=EndpointRoute.MODELS + "/{model:path}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Model,
    responses=get_documentation_responses([ModelNotFoundHTTPException]),
)
async def get_model(
    model: str = Path(description="The name of the model to get."),
    get_one_model_use_case: GetOneModelUseCase = Depends(get_one_model_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> JSONResponse:
    """
    Get a model by name and provide basic information.
    """
    command = GetOneModelCommand(authenticated_user=authenticated_user, name=model)
    try:
        result = await get_one_model_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_model use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "model_name": model,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case GetOneModelUseCaseSuccess(model):
            return JSONResponse(content=Model.model_validate(model, from_attributes=True).model_dump(), status_code=200)
        case ModelNotFoundError(name):
            raise ModelNotFoundHTTPException(name=name)
