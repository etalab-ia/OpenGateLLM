from typing import Annotated

from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.helpers._documentmanager import DocumentManager
from api.schemas.core.documents import FileType
from api.schemas.parse import CreateParseForm, ParsedDocument
from api.utils.context import global_context
from api.utils.dependencies import get_document_manager
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.PARSE.title()])


@router.post(
    path=EndpointRoute.PARSE,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=ParsedDocument,
    deprecated=True,
)
async def parse(
    request: Request,
    data: Annotated[CreateParseForm, Depends(CreateParseForm.as_form)],
    document_manager: DocumentManager = Depends(get_document_manager),
) -> JSONResponse:
    """
    Parse a PDF file into markdown.
    """

    document_manager.parser_manager.check_file_type(file=data.file, type=FileType.PDF)
    document = await global_context.parser.parse(file=data.file, force_ocr=data.force_ocr, page_range=data.page_range)

    return JSONResponse(content=document.model_dump(), status_code=200)
