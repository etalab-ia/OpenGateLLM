from typing import Literal

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._documentmanager import DocumentManager
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.schemas.collections import Collection, CollectionRequest, Collections, CollectionUpdateRequest, CollectionVisibility
from api.utils.context import request_context
from api.utils.dependencies import get_document_manager, get_elasticsearch_client, get_elasticsearch_vector_store, get_postgres_session
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.COLLECTIONS.title()])


@router.post(path=EndpointRoute.COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=201)
async def create_collection(
    request: Request,
    body: CollectionRequest,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    document_manager: DocumentManager = Depends(get_document_manager),
) -> JSONResponse:
    """
    Create a new collection.
    """
    collection_id = await document_manager.create_collection(
        postgres_session=postgres_session,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(status_code=201, content={"id": collection_id})


@router.get(
    path=EndpointRoute.COLLECTIONS + "/{collection_id}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Collection,
)
async def get_collection(
    request: Request,
    collection_id: int = Path(..., description="The collection ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    document_manager: DocumentManager = Depends(get_document_manager),
) -> JSONResponse:
    """
    Get a collection by ID.
    """
    collections = await document_manager.get_collections(
        postgres_session=postgres_session,
        collection_id=collection_id,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(status_code=200, content=collections[0].model_dump())


@router.get(path=EndpointRoute.COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Collections)
async def get_collections(
    request: Request,
    name: str = Query(default=None, description="Filter by collection name."),
    visibility: CollectionVisibility | None = Query(default=None, description="Filter by collection visibility."),
    offset: int = Query(default=0, ge=0, description="The offset of the collections to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the collections to get."),
    order_by: Literal["id", "name", "created", "updated"] = Query(default="id", description="The order by field to sort the collections by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the collections by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    document_manager: DocumentManager = Depends(get_document_manager),
) -> JSONResponse:
    """
    Get list of collections.
    """
    data = await document_manager.get_collections(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        collection_name=name,
        visibility=visibility,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(status_code=200, content=Collections(data=data).model_dump())


@router.delete(path=EndpointRoute.COLLECTIONS + "/{collection_id}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_collection(
    request: Request,
    collection_id: int = Path(..., description="The collection ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    document_manager: DocumentManager = Depends(get_document_manager),
) -> Response:
    """
    Delete a collection.
    """
    await document_manager.delete_collection(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        user_id=request_context.get().user_info.id,
        collection_id=collection_id,
    )

    return Response(status_code=204)


@router.patch(path=EndpointRoute.COLLECTIONS + "/{collection_id}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def update_collection(
    request: Request,
    collection_id: int = Path(..., description="The collection ID"),
    body: CollectionUpdateRequest = Body(..., description="The collection to update."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    document_manager: DocumentManager = Depends(get_document_manager),
) -> Response:
    """
    Update a collection.
    """
    await document_manager.update_collection(
        postgres_session=postgres_session,
        user_id=request_context.get().user_info.id,
        collection_id=collection_id,
        name=body.name,
        visibility=body.visibility,
        description=body.description,
    )

    return Response(status_code=204)
