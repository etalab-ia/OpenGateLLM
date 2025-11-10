from fastapi import APIRouter, Depends, File, Form, Path, Query, Request, Response, Security, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.schemas.collections import Collection, CollectionName, Collections, CollectionVisibility
from api.sql.session import get_db_session
from api.utils.context import global_context, request_context
from api.utils.exceptions import CollectionNotFoundException
from api.utils.variables import ENDPOINT__COLLECTIONS, ROUTER__COLLECTIONS

router = APIRouter(prefix="/v1", tags=[ROUTER__COLLECTIONS.title()])


@router.post(path=ENDPOINT__COLLECTIONS, dependencies=[Security(dependency=AccessController())], status_code=201)
async def create_collection(
    request: Request,
    name: CollectionName | None = Form(..., description="New name for the collection"),
    visibility: CollectionVisibility = Form(CollectionVisibility.PRIVATE, description="Visibility for the collection"),
    description: str | None = Form(default=None, description="Description for the collection"),
    file: UploadFile | None = File(default=None, description="Parquet file containing documents to add to the collection"),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Create a new collection.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    collection_id = await global_context.document_manager.create_collection(
        session=session,
        name=name,
        visibility=visibility,
        description=description,
        user_id=request_context.get().user_info.id,
    )
    response_data = {"id": collection_id, "details": {}}

    if file is not None:
        try:
            file_details = await global_context.document_manager.update_collection_from_parquet(
                session=session,
                user_id=request_context.get().user_info.id,
                collection_id=collection_id,
                parquet_file=file,
                force_update=True,
            )
            # Remove deleted_documents and updated_documents from response as they are not relevant on creation
            del file_details["deleted_documents"]
            del file_details["updated_documents"]
            response_data["details"] = file_details
        except Exception as e:
            # Delete the created collection if any error occurs during file processing
            await global_context.document_manager.delete_collection(
                session=session,
                user_id=request_context.get().user_info.id,
                collection_id=collection_id,
            )
            raise e

    return JSONResponse(status_code=201, content=response_data)


@router.get(
    path=ENDPOINT__COLLECTIONS + "/{collection}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Collection,
)
async def get_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get a collection by ID.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    collections = await global_context.document_manager.get_collections(
        session=session,
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
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get list of collections.
    """
    if not global_context.document_manager:  # no vector store available
        data = []
    else:
        data = await global_context.document_manager.get_collections(
            session=session,
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
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Delete a collection.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    await global_context.document_manager.delete_collection(
        session=session,
        user_id=request_context.get().user_info.id,
        collection_id=collection,
    )

    return Response(status_code=204)


@router.patch(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=AccessController())], status_code=200)
async def update_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    name: CollectionName | None = Form(default=None, description="New name for the collection"),
    visibility: CollectionVisibility | None = Form(default=None, description="New visibility for the collection"),
    description: str | None = Form(default=None, description="New description for the collection"),
    file: UploadFile | None = File(default=None, description="Parquet file containing documents to update"),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Update a collection.
    Requirements for the parquet file:
    - Each parquet file must contain complete documents (all chunks for a document must be in the same file).
    - Chunk IDs must be sequential for each document.
    - The parquet file must contain 'document_name' and 'content' columns which are repectively the name of the document and the text content to embed.
    - Optionally, the parquet file can contain a 'chunk_index' column to specify chunk order within each document.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    response_data = {"updated": [], "details": {}}

    # Track which fields are being updated
    update_metadatas = {}
    if name is not None:
        update_metadatas["name"] = name
    if visibility is not None:
        update_metadatas["visibility"] = visibility
    if description is not None:
        update_metadatas["description"] = description

    if file is not None:
        file_details = await global_context.document_manager.update_collection_from_parquet(
            session=session,
            user_id=request_context.get().user_info.id,
            collection_id=collection,
            parquet_file=file,
        )
        response_data["updated"].append("documents")
        response_data["details"] = file_details

    if update_metadatas:
        await global_context.document_manager.update_collection(
            session=session,
            user_id=request_context.get().user_info.id,
            collection_id=collection,
            **update_metadatas,
        )
        response_data["updated"].extend(update_metadatas.keys())

    return JSONResponse(status_code=200, content=response_data)


@router.put(path=ENDPOINT__COLLECTIONS + "/{collection}", dependencies=[Security(dependency=AccessController())], status_code=200)
async def force_update_collection(
    request: Request,
    collection: int = Path(..., description="The collection ID"),
    file: UploadFile | None = File(..., description="Parquet file containing documents and chunks to update"),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Force update collection documents from a parquet file.
    All existing documents in the collection will be deleted first.

    Requirements:
    - Each parquet file must contain complete documents (all chunks for a document must be in the same file).
    - Chunk IDs must be sequential for each document.
    - The parquet file must contain 'document_name' and 'content' columns which are repectively the name of the document and the text content to embed.
    - Optionally, the parquet file can contain a 'chunk_index' column to specify chunk order within each document.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    file_details = await global_context.document_manager.update_collection_from_parquet(
        session=session,
        user_id=request_context.get().user_info.id,
        collection_id=collection,
        parquet_file=file,
        force_update=True,
    )

    return JSONResponse(status_code=200, content={"updated": [], "details": file_details})
