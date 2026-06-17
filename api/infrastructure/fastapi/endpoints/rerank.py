from contextvars import ContextVar
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.dependencies import create_rerank_use_case_factory, get_request_context
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.infrastructure.fastapi import AccessController
from api.infrastructure.fastapi.context import RequestContext
from api.infrastructure.fastapi.decorators import hooks
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import (
    InsufficientBudgetHTTPException,
    InternalServerHTTPException,
    ModelIsTooBusyExceptionHTTPException,
    ModelNotFoundHTTPException,
    RateLimitExceededHTTPException,
    WrongModelTypeHTTPException,
)
from api.infrastructure.fastapi.schemas.rerank import CreateRerankBody, RerankResponse
from api.use_cases.reranks import CreateRerankCommand, CreateRerankUseCase, CreateRerankUseCaseSuccess
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=[RouterName.RERANK.title()])


@router.post(
    path=EndpointRoute.RERANK,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses(
        [
            ModelIsTooBusyExceptionHTTPException,
            ModelNotFoundHTTPException,
            RateLimitExceededHTTPException,
            WrongModelTypeHTTPException,
            InsufficientBudgetHTTPException,
        ]
    ),
    response_model=RerankResponse,
)
@hooks(postgres_session_provider=get_postgres_session)
async def create_rerank(
    body: CreateRerankBody = Body(description="The rerank creation request."),
    create_rerank_use_case: CreateRerankUseCase = Depends(create_rerank_use_case_factory),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    try:
        command = CreateRerankCommand(
            query=body.query,
            documents=body.documents,
            model=body.model,
            top_n=body.top_n,
            request_context=request_context,
        )
        result = await create_rerank_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing rerank use case",
            extra={
                "authenticated_user_id": request_context.get().user.id,
                "model_name": body.model,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateRerankUseCaseSuccess(data=data, headers=headers):
            return JSONResponse(content=RerankResponse.model_validate(data.model_dump()).model_dump(), status_code=200, headers=headers)
        case NoAvailableProviderError():
            raise ModelIsTooBusyExceptionHTTPException()
        case ProviderAdapterValidationRequestError(errors=errors):
            raise HTTPException(status_code=422, detail=jsonable_encoder(errors))
        case ProviderAdapterValidationResponseError(errors=errors):
            raise HTTPException(status_code=422, detail=jsonable_encoder(errors))
        case RouterRateLimitExceededError(id=_, limit_type=limit_type, headers=headers):
            raise RateLimitExceededHTTPException(limit_type=limit_type, headers=headers)
        case RouterNotFoundError():
            raise ModelNotFoundHTTPException(name=body.model)
        case RouterHasNoProvidersError():
            raise ModelNotFoundHTTPException(name=body.model)
        case RouterHasWrongTypeError(actual_type=actual_type, expected_type=expected_type):
            raise WrongModelTypeHTTPException(expected_type=expected_type, actual_type=actual_type)
        case UserHasNoAccessToRouterError():
            raise ModelNotFoundHTTPException(name=body.model)
        case UserHasInsufficientBudgetError():
            raise InsufficientBudgetHTTPException()
        case TooBusyModelError(detail=detail):
            raise ModelIsTooBusyExceptionHTTPException()
        case StatusCodeModelError(status_code=status_code, detail=detail):
            raise HTTPException(status_code=status_code, detail=detail)
        case UnknownModelError(detail=detail):
            raise HTTPException(status_code=500, detail=detail)
