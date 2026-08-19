import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse

from api.dependencies import create_audio_transcriptions_use_case_factory, get_postgres_session
from api.domain.audio.entities import CreateAudioTranscriptionsFile
from api.domain.audio.errors import AudioFileSizeLimitExceededError
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
    FileSizeLimitExceededHTTPException,
    InsufficientBudgetHTTPException,
    InternalServerHTTPException,
    ModelIsTooBusyExceptionHTTPException,
    ModelNotFoundHTTPException,
    RateLimitExceededHTTPException,
    WrongModelTypeHTTPException,
)
from api.infrastructure.fastapi.schemas.audio import AudioTranscriptionsResponse, CreateAudioTranscriptionsForm
from api.use_cases.audio import (
    CreateAudioTranscriptionsCommand,
    CreateAudioTranscriptionsJsonUseCaseSuccess,
    CreateAudioTranscriptionsTextUseCaseSuccess,
    CreateAudioTranscriptionsUseCase,
)
from api.utils.variables import EndpointRoute, RouterName

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=[RouterName.AUDIO.title()])


@router.post(
    path=EndpointRoute.AUDIO_TRANSCRIPTIONS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses(
        [
            ModelIsTooBusyExceptionHTTPException,
            ModelNotFoundHTTPException,
            RateLimitExceededHTTPException,
            WrongModelTypeHTTPException,
            InsufficientBudgetHTTPException,
            FileSizeLimitExceededHTTPException,
        ]
    ),
    response_model=AudioTranscriptionsResponse,
)
@hooks(postgres_session_provider=get_postgres_session)
async def create_audio_transcription(
    data: Annotated[CreateAudioTranscriptionsForm, Depends(CreateAudioTranscriptionsForm.as_form)],
    create_audio_transcriptions_use_case: CreateAudioTranscriptionsUseCase = Depends(create_audio_transcriptions_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
) -> JSONResponse:
    try:
        payload = data.model_dump(mode="json", exclude={"file"})
        payload["file"] = CreateAudioTranscriptionsFile(
            name=data.file.filename,
            file=data.file.file,
            content_type=data.file.content_type,
            size=data.file.size,
        )

        command = CreateAudioTranscriptionsCommand(payload=payload, authenticated_user=authenticated_user)
        result = await create_audio_transcriptions_use_case.execute(command)
    except Exception as e:
        logger.exception(
            "Unexpected error while executing audio transcriptions use case",
            extra={
                "authenticated_user_id": authenticated_user.id,
                "model_name": data.model,
                "error_type": type(e).__name__,
            },
        )
        raise InternalServerHTTPException()

    match result:
        case CreateAudioTranscriptionsJsonUseCaseSuccess(data=data, headers=headers, media_type=media_type):
            return JSONResponse(
                content=AudioTranscriptionsResponse.model_validate(data.model_dump()).model_dump(),
                status_code=200,
                headers=headers,
                media_type=media_type,
            )
        case CreateAudioTranscriptionsTextUseCaseSuccess(text=text, headers=headers, media_type=media_type):
            return PlainTextResponse(content=text, status_code=200, headers=headers, media_type=media_type)
        case AudioFileSizeLimitExceededError(size=size, expected_size=expected_size):
            raise FileSizeLimitExceededHTTPException(size=size, expected_size=expected_size)
        case NoAvailableProviderError():
            raise ModelIsTooBusyExceptionHTTPException()
        case ProviderAdapterValidationRequestError(errors=errors):
            raise HTTPException(status_code=422, detail=jsonable_encoder(errors))
        case ProviderAdapterValidationResponseError(errors=errors):
            raise HTTPException(status_code=422, detail=jsonable_encoder(errors))
        case RouterRateLimitExceededError(id=_, limit_type=limit_type, headers=headers):
            raise RateLimitExceededHTTPException(limit_type=limit_type, headers=headers)
        case RouterNotFoundError():
            raise ModelNotFoundHTTPException(name=data.model)
        case RouterHasNoProvidersError():
            raise ModelNotFoundHTTPException(name=data.model)
        case RouterHasWrongTypeError(actual_type=actual_type, expected_type=expected_type):
            raise WrongModelTypeHTTPException(expected_type=expected_type, actual_type=actual_type)
        case UserHasNoAccessToRouterError():
            raise ModelNotFoundHTTPException(name=data.model)
        case UserHasInsufficientBudgetError():
            raise InsufficientBudgetHTTPException()
        case TooBusyModelError(detail=detail):
            raise ModelIsTooBusyExceptionHTTPException()
        case StatusCodeModelError(status_code=status_code, detail=detail):
            raise HTTPException(status_code=status_code, detail=detail)
        case UnknownModelError(detail=detail):
            raise HTTPException(status_code=500, detail=detail)
