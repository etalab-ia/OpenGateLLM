import base64

from fastapi import APIRouter, Request, Security, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import pymupdf

from api.helpers._accesscontroller import AccessController
from api.schemas.core.documents import FileType
from api.schemas.ocr import DPIForm, ModelForm, PromptForm
from api.schemas.parse import FileForm, ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from api.schemas.usage import Usage
from api.utils.context import global_context
from api.utils.exceptions import FileSizeLimitExceededException, TaskFailedException
from api.utils.variables import ENDPOINT__OCR, ROUTER__OCR
from api.services.model_invocation import invoke_model_request

router = APIRouter(prefix="/v1", tags=[ROUTER__OCR.upper()])


@router.post(path=ENDPOINT__OCR, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=ParsedDocument)
async def ocr(request: Request, file: UploadFile = FileForm, model: str = ModelForm, dpi: int = DPIForm, prompt: str = PromptForm) -> JSONResponse:
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
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(img_byte_arr).decode('utf-8')}"}},
                    ],
                }
            ],
            "n": 1,
            "stream": False,
        }
        user_info = getattr(request.state, "user", None)
        user_priority = getattr(user_info, "priority", 0) if user_info else 0
        try:
            client = await invoke_model_request(model_name=model, endpoint=ENDPOINT__OCR, user_priority=user_priority)
        except TaskFailedException as e:
            return JSONResponse(content=e.detail, status_code=e.status_code)
        client.endpoint = ENDPOINT__OCR
        response = await client.forward_request(method="POST", json=payload)
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
