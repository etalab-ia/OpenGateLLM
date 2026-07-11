from contextvars import ContextVar
from http import HTTPMethod

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._searchtool import SearchTool
from api.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from api.helpers.models import ModelRegistry
from api.schemas.chat import ChatCompletion, ChatCompletionChunk, CreateChatCompletion
from api.schemas.core.context import RequestContext
from api.schemas.core.models import RequestContent
from api.schemas.exception import HTTPExceptionModel
from api.utils.configuration import configuration
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.exceptions import CollectionNotFoundException, ModelIsTooBusyException, ModelNotFoundException, WrongModelTypeException
from api.utils.hooks_decorator import hooks
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.CHAT.title()])


@router.post(
    path=EndpointRoute.CHAT_COMPLETIONS,
    status_code=200,
    dependencies=[Security(dependency=AccessController())],
    response_model=ChatCompletion | ChatCompletionChunk,
    responses={
        404: {"model": HTTPExceptionModel, "description": f"{ModelNotFoundException().detail} {CollectionNotFoundException().detail}"},
        WrongModelTypeException().status_code: {"model": HTTPExceptionModel, "description": WrongModelTypeException().detail},
        ModelIsTooBusyException().status_code: {"model": HTTPExceptionModel, "description": ModelIsTooBusyException().detail},
    },
)
@hooks
async def chat_completions(
    request: Request,
    body: CreateChatCompletion,
    model_registry: ModelRegistry = Depends(get_model_registry),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    redis_client: AsyncRedis = Depends(get_redis_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse | StreamingResponseWithStatusCode:
    """Creates a model response for the given chat conversation."""
    model_provider = await model_registry.get_model_provider(
        model=body.model,
        endpoint=EndpointRoute.CHAT_COMPLETIONS,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )

    request_content = RequestContent(method=HTTPMethod.POST, endpoint=EndpointRoute.CHAT_COMPLETIONS, body=body.model_dump(), model=body.model)

    if configuration.settings.search_opengaterag_url:
        search_tool = SearchTool(
            opengaterag_url=configuration.settings.search_opengaterag_url,
            postgres_session=postgres_session,
            user_id=request_context.get().user_info.id,
            secret_key=configuration.settings.auth_secret_key,
        )
        request_content = await search_tool.call(request_content=request_content)

    await postgres_session.close()

    if body.stream:
        stream_iter = model_provider.forward_stream(request_content=request_content, redis_client=redis_client)
        return StreamingResponseWithStatusCode(content=stream_iter, media_type="text/event-stream")

    response = await model_provider.forward_request(request_content=request_content, redis_client=redis_client)
    return JSONResponse(content=response.json(), status_code=response.status_code)
