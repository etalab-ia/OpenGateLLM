from fastapi import APIRouter, Request, Security, HTTPException
from fastapi.responses import JSONResponse

from api.helpers._accesscontroller import AccessController
from api.schemas.rerank import RerankRequest, Reranks
from api.utils.context import global_context
from api.utils.variables import ENDPOINT__RERANK, ROUTER__RERANK

router = APIRouter(prefix="/v1", tags=[ROUTER__RERANK.title()])


@router.post(path=ENDPOINT__RERANK, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Reranks)
async def rerank(request: Request, body: RerankRequest) -> JSONResponse:
    """
    Creates an ordered array with each text assigned a relevance score, based on the query.
    """
    model = await global_context.model_registry(model=body.model)
    client = model.get_client(endpoint=ENDPOINT__RERANK)

    # Validate batch size against client's max_items if provided
    items_count = len(body.input)
    max_items = getattr(client, "max_items", None)
    if max_items is not None and items_count > max_items:
        raise HTTPException(
            status_code=400,
            detail=f"Too many items in rerank request: {items_count} provided, maximum allowed is {max_items}. Split the batch into chunks of at most {max_items} texts.",
        )

    response = await client.forward_request(method="POST", json=body.model_dump())

    return JSONResponse(content=Reranks(**response.json()).model_dump(), status_code=response.status_code)
