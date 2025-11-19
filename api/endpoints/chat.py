from contextvars import ContextVar

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._streamingresponsewithstatuscode import StreamingResponseWithStatusCode
from api.helpers.models import ModelRegistry
from api.schemas.chat import ChatCompletion, ChatCompletionChunk, CreateChatCompletion
from api.schemas.core.context import RequestContext
from api.schemas.exception import HTTPExceptionModel
from api.schemas.search import Search
from api.utils.context import global_context
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.exceptions import CollectionNotFoundException, ModelIsTooBusyException, ModelNotFoundException, WrongModelTypeException
from api.utils.hooks_decorator import hooks
from api.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ROUTER__CHAT

router = APIRouter(prefix="/v1", tags=[ROUTER__CHAT.title()])


@router.post(
    path=ENDPOINT__CHAT_COMPLETIONS,
    status_code=200,
    dependencies=[Security(dependency=AccessController())],
    response_model=ChatCompletion | ChatCompletionChunk,
    # fmt: off
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
    """Creates a model response for the given chat conversation.

    **Important**: any others parameters are authorized, depending on the model backend. For example, if model is support by vLLM backend, additional
    fields are available (see https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py#L209). Similarly, some defined fields
    may be ignored depending on the backend used and the model support.
    """

    # retrieval augmentation generation
    async def retrieval_augmentation_generation(
        initial_body: CreateChatCompletion,
        inner_postgres_session: AsyncSession,
        inner_redis_client: AsyncRedis,
        inner_model_registry: ModelRegistry,
        inner_request_context: ContextVar[RequestContext],
    ) -> tuple[CreateChatCompletion, list[Search]]:
        results = []
        if initial_body.search:
            if not global_context.document_manager:
                raise CollectionNotFoundException()

            results = await global_context.document_manager.search_chunks(
                request_context=request_context,
                postgres_session=inner_postgres_session,
                redis_client=inner_redis_client,
                model_registry=inner_model_registry,
                collection_ids=initial_body.search_args.collections,
                prompt=initial_body.messages[-1]["content"],
                method=initial_body.search_args.method,
                limit=initial_body.search_args.limit,
                offset=initial_body.search_args.offset,
                rff_k=initial_body.search_args.rff_k,
                web_search=initial_body.search_args.web_search,
            )
            if results:
                chunks = "\n".join([result.chunk.content for result in results])
                initial_body.messages[-1]["content"] = initial_body.search_args.template.format(
                    prompt=initial_body.messages[-1]["content"], chunks=chunks
                )

        new_body = initial_body.model_dump()
        new_body.pop("search", None)
        new_body.pop("search_args", None)

        results = [result.model_dump() for result in results]

        return new_body, results

    body, results = await retrieval_augmentation_generation(
        initial_body=body,
        inner_postgres_session=postgres_session,
        inner_redis_client=redis_client,
        inner_model_registry=model_registry,
        inner_request_context=request_context,
    )
    additional_data = {"search_results": results} if results else {}
    model_provider = await model_registry.get_model_provider(
        model=body["model"],
        endpoint=ENDPOINT__CHAT_COMPLETIONS,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )

    if not body.get("stream", False):
        response = await model_provider.forward_request(
            method="POST",
            json=body,
            additional_data=additional_data,
            endpoint=ENDPOINT__CHAT_COMPLETIONS,
            redis_client=redis_client,
        )
        return JSONResponse(content=response.json(), status_code=response.status_code)
    else:
        stream_iter = model_provider.forward_stream(
            method="POST",
            json=body,
            additional_data=additional_data,
            endpoint=ENDPOINT__CHAT_COMPLETIONS,
            redis_client=redis_client,
        )
        return StreamingResponseWithStatusCode(content=stream_iter, media_type="text/event-stream")
