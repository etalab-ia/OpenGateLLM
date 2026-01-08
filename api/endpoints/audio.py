from contextvars import ContextVar
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Request, Security, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.audio import (
    AudioTranscription,
    AudioTranscriptionLanguage,
)
from api.schemas.core.context import RequestContext
from api.schemas.core.models import RequestContent
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.variables import ENDPOINT__AUDIO_TRANSCRIPTIONS, ROUTER__AUDIO

router = APIRouter(prefix="/v1", tags=[ROUTER__AUDIO.title()])


# fmt: off
@router.post(path=ENDPOINT__AUDIO_TRANSCRIPTIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=AudioTranscription)
async def audio_transcriptions(
    request: Request,
    file: UploadFile = File(description="The audio file object (not file name) to transcribe, in one of these formats: mp3 or wav."),
    model: str = Form(default=..., description="ID of the model to use. Call `/v1/models` endpoint to get the list of available models, only `automatic-speech-recognition` model type is supported."),
    language: AudioTranscriptionLanguage = Form(default=AudioTranscriptionLanguage.EMPTY, description="The language of the output audio. If the output language is different than the audio language, the audio language will be translated into the output language. Supplying the output language in ISO-639-1 (e.g. en, fr) format will improve accuracy and latency."),
    prompt: str | None = Form(default=None, description="An optional text to tell the model what to do with the input audio. Default is `Transcribe this audio in this language : {language}`"),
    response_format: Literal["json", "text"] = Form(default="json", description="The format of the transcript output, in one of these formats: `json` or `text`."),
    temperature: float | None = Form(default=None, ge=0, le=1, description="The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit."),
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse | PlainTextResponse:
    """
    Transcribes audio into the input language.
    """
    model_provider = await model_registry.get_model_provider(
        model=model,
        endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context
    )

    file_content = await file.read()
    form = {"model": model, "response_format": response_format, "temperature": temperature, "language": language.value, "prompt": prompt}

    response = await model_provider.forward_request(
        request_content=RequestContent(
            method="POST",
            model=model,
            endpoint=ENDPOINT__AUDIO_TRANSCRIPTIONS,
            files={"file": (file.filename, file_content, file.content_type)},
            form=form,
        ),
        redis_client=redis_client,
    )

    if response_format == "text":
        response = PlainTextResponse(content=response.json()["text"], status_code=response.status_code)
    else:
        response = JSONResponse(content=AudioTranscription(**response.json()).model_dump(), status_code=response.status_code)

    return response
