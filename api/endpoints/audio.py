from contextvars import ContextVar
from typing import Literal

from fastapi import APIRouter, Depends, File, Request, Security, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.audio import (
    AudioTranscription,
    AudioTranscriptionLanguage,
    AudioTranscriptionLanguageForm,
    AudioTranscriptionModelForm,
    AudioTranscriptionPromptForm,
    AudioTranscriptionResponseFormatForm,
    AudioTranscriptionTemperatureForm,
    AudioTranscriptionTimestampGranularitiesForm,
)
from api.schemas.core.context import RequestContext
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.hooks_decorator import hooks
from api.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ROUTER__AUDIO

router = APIRouter(prefix="/v1", tags=[ROUTER__AUDIO.title()])


@router.post(path=ENDPOINT__AUDIO_TRANSCRIPTIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=AudioTranscription)  # fmt: off
@hooks
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
    model: str = AudioTranscriptionModelForm,
    language: AudioTranscriptionLanguage | Literal[""] = AudioTranscriptionLanguageForm,
    prompt: str = AudioTranscriptionPromptForm,
    response_format: Literal["json", "text"] = AudioTranscriptionResponseFormatForm,
    temperature: float = AudioTranscriptionTemperatureForm,
    timestamp_granularities: list[str] = AudioTranscriptionTimestampGranularitiesForm,
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse | PlainTextResponse:
    """
    Transcribes audio into the input language.
    """

    file_content = await file.read()

    payload = {
        "model": model,
        "response_format": response_format,
        "temperature": temperature,
        "timestamp_granularities": timestamp_granularities,
    }
    if language != "":
        payload["language"] = language.value

    model_provider = await model_registry.get_model_provider(
        model=model,
        endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )

    response = await model_provider.forward_request(
        method="POST",
        files={"file": (file.filename, file_content, file.content_type)},
        data=payload,
        endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS,
        redis_client=redis_client,
    )

    if response_format == "text":
        response = PlainTextResponse(content=response.text, status_code=response.status_code)
    else:
        response = JSONResponse(content=AudioTranscription(**response.json()).model_dump(), status_code=response.status_code)

    return response
