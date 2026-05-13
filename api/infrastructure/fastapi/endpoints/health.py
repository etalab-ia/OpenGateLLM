from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse

from api.dependencies import get_health_models_use_case_factory, get_request_context
from api.domain.user.errors import UserExpiredError
from api.infrastructure.fastapi.access import get_current_key
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import AccountExpiredHTTPException
from api.use_cases.health import GetHealthModelsCommand, GetHealthModelsUseCase, GetHealthModelsUseCaseSuccess
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(tags=[RouterName.MONITORING.title()])


@router.get(path=EndpointRoute.HEALTH, status_code=200)
def get_health() -> JSONResponse:
    return JSONResponse(content={"status": "ok"}, status_code=200)


@router.get(
    path=EndpointRoute.HEALTH_MODELS,
    dependencies=[Security(dependency=get_current_key)],
    status_code=200,
    responses=get_documentation_responses([]),
)
async def get_health_models(
    request: Request,
    get_health_models_use_case: GetHealthModelsUseCase = Depends(get_health_models_use_case_factory),
    request_context: RequestContext = Depends(get_request_context),
) -> JSONResponse:
    """
    Get a model by name and provide basic information.
    """

    result = await get_health_models_use_case.execute(command=GetHealthModelsCommand(user_id=request_context.get().user_id))

    match result:
        case GetHealthModelsUseCaseSuccess():
            return JSONResponse(content=[model.model_dump() for model in result.models], status_code=200)
        case UserExpiredError():
            raise AccountExpiredHTTPException()
