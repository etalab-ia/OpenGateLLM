import base64
from contextvars import ContextVar

from fastapi import APIRouter, Depends, HTTPException, Request, Security, UploadFile
from fastapi.responses import JSONResponse
import pymupdf
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers.models import ModelRegistry
from api.schemas.core.context import RequestContext
from api.schemas.core.documents import FileType
from api.schemas.exception import HTTPExceptionModel
from api.schemas.ocr import OCR, CreateOCR, DPIForm, ModelForm, PromptForm
from api.schemas.parse import FileForm, ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from api.schemas.usage import Usage
from api.utils.context import global_context
from api.utils.dependencies import get_model_registry, get_postgres_session, get_redis_client, get_request_context
from api.utils.exceptions import (
    FileSizeLimitExceededException,
    ModelIsTooBusyException,
    ModelNotFoundException,
    WrongModelTypeException,
)
from api.utils.hooks_decorator import hooks
from api.utils.variables import ENDPOINT__OCR, ENDPOINT__OCR_BETA, ROUTER__OCR, ENDPOINT__CHAT_COMPLETIONS

router = APIRouter(prefix="/v1", tags=[ROUTER__OCR.upper()])


@hooks
@router.post(
    path=ENDPOINT__OCR,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    responses={
        ModelNotFoundException().status_code: {"model": HTTPExceptionModel, "description": ModelNotFoundException().detail},
        WrongModelTypeException().status_code: {"model": HTTPExceptionModel, "description": WrongModelTypeException().detail},
        ModelIsTooBusyException().status_code: {"model": HTTPExceptionModel, "description": ModelIsTooBusyException().detail},
    },
    response_model=OCR,
)
async def ocr(
    request: Request,
    body: CreateOCR,
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Extracts text from files using OCR.
    """
    model_provider = await model_registry.get_model_provider(
        model=body.model,
        endpoint=ENDPOINT__OCR,
        postgres_session=postgres_session,
        redis_client=redis_client,
        request_context=request_context,
    )
    response = await model_provider.forward_request(method="POST", json=body.model_dump(), endpoint=ENDPOINT__OCR, redis_client=redis_client)

    return JSONResponse(content=OCR(**response.json()).model_dump(), status_code=response.status_code)


@router.post(path=ENDPOINT__OCR_BETA, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=ParsedDocument)
@hooks
async def ocr_beta(
    request: Request,
    file: UploadFile = FileForm,
    model: str = ModelForm,
    dpi: int = DPIForm,
    prompt: str = PromptForm,
    model_registry: ModelRegistry = Depends(get_model_registry),
    redis_client: AsyncRedis = Depends(get_redis_client),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Extracts text from PDF files using OCR.
    """
    # check if file is a pdf (raises UnsupportedFileTypeException if not a PDF)
    global_context.document_manager.parser_manager._detect_file_type(file=file, type=FileType.PDF)

    # check file size
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    file_content = await file.read()
    pdf = pymupdf.open(stream=file_content, filetype="pdf")
    document = ParsedDocument(data=[], usage=Usage())
    for i, page in enumerate(pdf):
        image = page.get_pixmap(dpi=dpi)
        img_byte_arr = image.tobytes("png")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(img_byte_arr).decode("utf-8")}"}},
                    ],
                }
            ],
            "n": 1,
            "stream": False,
        }

        model_provider = await model_registry.get_model_provider(
            model=model,
            endpoint=ENDPOINT__OCR_BETA,
            postgres_session=postgres_session,
            redis_client=redis_client,
            request_context=request_context,
        )

        response = await model_provider.forward_request(method="POST", json=payload, endpoint=ENDPOINT__CHAT_COMPLETIONS, redis_client=redis_client)
        status = response.status_code
        body_json = response.json()
        if status // 100 != 2:
            pdf.close()
            raise HTTPException(status_code=status, detail=body_json.get("detail", "OCR request failed"))
        text = body_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        document.data.append(
            ParsedDocumentPage(
                content=text,
                images={},
                metadata=ParsedDocumentMetadata(page=i, document_name=file.filename, **pdf.metadata),
            )
        )
        if body_json.get("usage"):
            document.usage = Usage(**body_json["usage"])
    pdf.close()
    return JSONResponse(content=document.model_dump(), status_code=200)
