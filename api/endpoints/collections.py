from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.collections import Collection, CollectionRequest, Collections, CollectionUpdateRequest, CollectionVisibility
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_postgres_session
from api.utils.exceptions import CollectionNotFoundException
from api.utils.variables import ENDPOINT__COLLECTIONS, ROUTER__COLLECTIONS

router = APIRouter(prefix="/v1", tags=[ROUTER__COLLECTIONS.title()])


@router.post(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=201)
async def create_collection(
    request: Request,
    body: CollectionRequest,
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Create a new collection.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    collection_id = await global_context.document_manager.create_collection(
        postgres_session=postgres_session,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(
    path=ENDPOINT__COLLECTIONS + "/{collection}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Collection,
)
async def get_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get a collection by ID.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    collections = await global_context.document_manager.get_collections(
        postgres_session=postgres_session,
        collection_id=collection,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(status_code=200, content=collections[0].model_dump())


@router.get(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Collections)
async def get_collections(
    request: Request,
    name: str = Query(default=None, description="Filter by collection name."),
    visibility: CollectionVisibility | None = Query(default=None, description="Filter by collection visibility."),
    offset: int = Query(default=0, ge=0, description="The offset of the collections to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the collections to get."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> JSONResponse:
    """
    Get list of collections.
    """
    if not global_context.document_manager:  # no vector store available
        data = []
    else:
        data = await global_context.document_manager.get_collections(
            postgres_session=postgres_session,
            user_id=request_context.get().user_info.id,
            collection_name=name,
            visibility=visibility,
            offset=offset,
            limit=limit,
        )

    return JSONResponse(status_code=200, content=Collections(data=data).model_dump())


@router.delete(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Delete a collection.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    await global_context.document_manager.delete_collection(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        collection_id=collection,
    )

    return Response(status_code=204)


@router.patch(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def update_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    body: CollectionUpdateRequest = Body(..., description="The collection to update."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> Response:
    """
    Update a collection.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    await global_context.document_manager.update_collection(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        collection_id=collection,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
    )

    return Response(status_code=204)
