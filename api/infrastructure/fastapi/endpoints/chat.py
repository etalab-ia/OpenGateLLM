from collections.abc import AsyncGenerator
from contextlib import aclosing

from fastapi import APIRouter, Body, Depends, HTTPException, Security
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from api.dependencies import create_chat_completions_use_case_factory
from api.domain.key.entities import Key
from api.domain.model.errors import StatusCodeModelError, TooBusyModelError, UnknownModelError
from api.domain.provider.entities import ProviderChunkResponse
from api.domain.provider.errors import (
    NoAvailableProviderError,
    ProviderAdapterValidationRequestError,
    ProviderAdapterValidationResponseError,
    UnsupportedProviderEndpointError,
)
from api.domain.router.errors import RouterHasNoProvidersError, RouterHasWrongTypeError, RouterNotFoundError, RouterRateLimitExceededError
from api.domain.user.errors import UserHasNoAccessToRouterError
from api.domain.user.views import AuthenticatedUserView
from api.infrastructure.fastapi._streamingresponsewithstatuscode import StreamChunk, StreamingResponseWithStatusCode
from api.infrastructure.fastapi.accesscontroller import AccessController
from api.infrastructure.fastapi.dependencies import get_authenticated_key, get_authenticated_user
from api.infrastructure.fastapi.documentation import get_documentation_responses
from api.infrastructure.fastapi.endpoints.exceptions import (
    ModelIsTooBusyExceptionHTTPException,
    ModelNotFoundHTTPException,
    RateLimitExceededHTTPException,
    UnsupportedProviderEndpointHTTPException,
    WrongModelTypeHTTPException,
)
from api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from api.infrastructure.fastapi.schemas.chat import ChatCompletionChunkResponse, ChatCompletionResponse, CreateChatCompletionsBody
from api.use_cases.chat import (
    CreateChatCompletionsCommand,
    CreateChatCompletionsStreamUseCaseSuccess,
    CreateChatCompletionsUseCase,
    CreateChatCompletionsUseCaseSuccess,
)

router = APIRouter(prefix="/v1", tags=[RouterName.CHAT.title()])


async def _as_stream_chunks(chunks: AsyncGenerator[ProviderChunkResponse]) -> AsyncGenerator[StreamChunk]:
    first_chunk = True

    async with aclosing(chunks):
        async for chunk in chunks:
            failed = chunk.status_code // 100 != 2

            if failed and first_chunk:
                yield chunk.content, chunk.status_code
                return

            line = f"event: error\ndata: {chunk.content}" if failed else chunk.content
            yield f"{line}\n\n", chunk.status_code
            first_chunk = False


@router.post(
    path=EndpointRoute.CHAT_COMPLETIONS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses=get_documentation_responses(
        [
            ModelIsTooBusyExceptionHTTPException,
            ModelNotFoundHTTPException,
            RateLimitExceededHTTPException,
            WrongModelTypeHTTPException,
        ]
    ),
    response_model=ChatCompletionResponse | ChatCompletionChunkResponse,
)
async def create_chat_completions(
    body: CreateChatCompletionsBody = Body(description="The chat completion request."),
    create_chat_completions_use_case: CreateChatCompletionsUseCase = Depends(create_chat_completions_use_case_factory),
    authenticated_user: AuthenticatedUserView = Depends(get_authenticated_user),
    authenticated_key: Key = Depends(get_authenticated_key),
) -> JSONResponse | StreamingResponseWithStatusCode:
    """Creates a model response for the given chat conversation."""
    command = CreateChatCompletionsCommand(payload=body.model_dump(), authenticated_user=authenticated_user, authenticated_key=authenticated_key)
    result = await create_chat_completions_use_case.execute(command)

    match result:
        case CreateChatCompletionsStreamUseCaseSuccess(chunks=chunks, headers=headers):
            return StreamingResponseWithStatusCode(
                content=_as_stream_chunks(chunks),
                media_type="text/event-stream",
                headers=headers,
            )
        case CreateChatCompletionsUseCaseSuccess(data=data, headers=headers):
            return JSONResponse(content=ChatCompletionResponse.model_validate(data.model_dump()).model_dump(), status_code=200, headers=headers)
        case NoAvailableProviderError():
            raise ModelIsTooBusyExceptionHTTPException()
        case ProviderAdapterValidationRequestError(errors=errors):
            raise HTTPException(status_code=422, detail=jsonable_encoder(errors))
        case ProviderAdapterValidationResponseError(errors=errors):
            raise HTTPException(status_code=422, detail=jsonable_encoder(errors))
        case UnsupportedProviderEndpointError(endpoint=endpoint, provider_type=provider_type):
            raise UnsupportedProviderEndpointHTTPException(endpoint=endpoint, provider_type=provider_type)
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
        case TooBusyModelError(detail=detail):
            raise ModelIsTooBusyExceptionHTTPException()
        case StatusCodeModelError(status_code=status_code, detail=detail):
            raise HTTPException(status_code=status_code, detail=detail)
        case UnknownModelError(detail=detail):
            raise HTTPException(status_code=500, detail=detail)
