import logging

from fastapi import APIRouter, Depends, Security
from fastapi.responses import JSONResponse

from api.dependencies import get_health_models_use_case_factory, get_request_context
from api.infrastructure.fastapi import AccessController
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import InternalServerHTTPException
from api.infrastructure.fastapi.schemas.health import ModelHealthStatus, ModelsHealthResponse
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)

router = APIRouter(tags=[RouterName.HEALTH.title()])


@router.get(path=EndpointRoute.HEALTH, status_code=200)
def get_health() -> JSONResponse:
    """
    Get the health of the API.
    """
    return JSONResponse(content={"status": "ok"}, status_code=200)


@router.get(
    path=EndpointRoute.HEALTH_MODELS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_health_models(
    get_health_models_use_case: GetHealthModelsUseCase = Depends(get_health_models_use_case_factory),
    request_context: RequestContext = Depends(get_request_context),
) -> JSONResponse:
    """
    Get the health of the models.
    """

    command = GetHealthModelsCommand(authenticated_user=request_context.get().user)
    try:
        result = await get_health_models_use_case.execute(command=command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing get_health_models use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()
    match result:
        case GetHealthModelsUseCaseSuccess(models):
            return JSONResponse(
                content=ModelsHealthResponse(data=[ModelHealthStatus.model_validate(model, from_attributes=True) for model in models]).model_dump(),
                status_code=200,
            )
