from contextvars import ContextVar
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse, PlainTextResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.audio import AudioTranscription, CreateAudioTranscription
from api.schemas.core.context import RequestContext
from api.schemas.core.models import RequestContent
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.AUDIO.title()])


@router.post(
    path=EndpointRoute.AUDIO_TRANSCRIPTIONS,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=AudioTranscription,
)
async def audio_transcriptions(
    request: Request,
    data: Annotated[CreateAudioTranscription, Depends(CreateAudioTranscription.as_form)],
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse | PlainTextResponse:
    """
    Transcribes audio into the input language.
    """
    model_provider = await model_registry.get_model_provider(
        model=data.model,
        endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )

    file_content = await data.file.read()

    response = await model_provider.forward_request(
        request_content=RequestContent(
            method="POST",
            model=data.model,
            endpoint=EndpointRoute.AUDIO_TRANSCRIPTIONS,
            files={"file": (data.file.filename, file_content, data.file.content_type)},
            form=data.model_dump(mode="json", exclude="file"),
        ),
        redis_client=redis_client,
    )

    if data.response_format == "text":
        response = PlainTextResponse(content=response.json()["text"], status_code=response.status_code)
    else:
        response = JSONResponse(content=AudioTranscription(**response.json()).model_dump(), status_code=response.status_code)

    return response
