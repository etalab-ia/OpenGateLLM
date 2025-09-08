from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.search import Searches, SearchRequest
from api.sql.session import get_db_session
from api.utils.context import global_context, request_context
from api.utils.exceptions import CollectionNotFoundException
from api.utils.variables import ENDPOINT__SEARCH, ROUTER__SEARCH

router = APIRouter(prefix="/v1", tags=[ROUTER__SEARCH.title()])


@router.post(path=ENDPOINT__SEARCH, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Searches)
async def search(request: Request, body: SearchRequest, session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    """
    Get relevant chunks from the collections and a query.
    """

    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    data = await global_context.document_manager.search_chunks(
        session=session,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        user_id=request_context.get().user_info.id,
        web_search=body.web_search,
    )
    usage = request_context.get().usage
    content = Searches(data=data, usage=usage)

    return JSONResponse(content=content.model_dump(), status_code=200)
