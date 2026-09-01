import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.dependencies import create_ocr_use_case_factory, get_router_rate_limiter
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.errors import NoAvailableProviderError, ProviderAdapterValidationRequestError, ProviderAdapterValidationResponseError
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasInsufficientBudgetError, UserHasNoAccessToRouterError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.decorators import hooks
from api.infrastructure.fastapi.dependencies import get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import (
    InsufficientBudgetHTTPException,
    InternalServerHTTPException,
    ModelIsTooBusyExceptionHTTPException,
    ModelNotFoundHTTPException,
    RateLimitExceededHTTPException,
    WrongModelTypeHTTPException,
)
from api.infrastructure.fastapi.schemas.ocr import CreateOCRBody, OCRResponse
from api.use_cases.ocr import CreateOCRCommand, CreateOCRUseCase, CreateOCRUseCaseSuccess
from api.utils.dependencies import get_postgres_session
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=[RouterName.OCR.upper()])


@router.post(
    path=EndpointRoute.OCR,
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
    response_model=OCRResponse,
)
@hooks(postgres_session_provider=get_postgres_session, router_rate_limiter_provider=get_router_rate_limiter)
async def create_ocr(
    body: CreateOCRBody = Body(description="The OCR creation request."),
    create_ocr_use_case: CreateOCRUseCase = Depends(create_ocr_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> JSONResponse:
    """
    Extracts text from files using Mistral Document AI pipeline
    """
    try:
        command = CreateOCRCommand(payload=body.model_dump(), authenticated_user=authenticated_user)
        result = await create_ocr_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing ocr use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "model_name": body.model,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateOCRUseCaseSuccess(data=data, headers=headers):
            return JSONResponse(content=OCRResponse.model_validate(data.model_dump()).model_dump(), status_code=200, headers=headers)
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
