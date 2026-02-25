from contextvars import ContextVar
from typing import Annotated, Literal

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from pydantic import StringConstraints
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers.models import ModelRegistry
from api.schemas.chunks import Chunks, ChunksResponse, CreateChunks
from api.schemas.core.context import RequestContext
from api.schemas.documents import CreateDocumentForm, Document, DocumentResponse, Documents
from api.utils.context import global_context
from api.utils.dependencies import (
    get_elasticsearch_client,
    get_elasticsearch_vector_store,
    get_model_registry,
    get_postgres_session,
    get_redis_client,
    get_request_context,
)
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.DOCUMENTS.title()])


@router.post(path=EndpointRoute.DOCUMENTS, status_code=201, dependencies=[Security(dependency=AccessController())], response_model=DocumentResponse)
async def create_document(
    request: Request,
    data: Annotated[CreateDocumentForm, Depends(CreateDocumentForm.as_form)],
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    redis_client: AsyncRedis = Depends(get_redis_client),
    model_registry: ModelRegistry = Depends(get_model_registry),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Upload a file, parse and split it into chunks, then create a document. If no file is provided, the document will be created without content, use POST `/v1/documents/{document_id}/chunks` to fill it.
    """
    document_id = await global_context.document_manager.create_document(
        file=data.file,
        name=data.name,
        collection_id=data.collection_id,
        disable_chunking=data.disable_chunking,
        chunk_size=data.chunk_size,
        chunk_min_size=data.chunk_min_size,
        chunk_overlap=data.chunk_overlap,
        is_separator_regex=data.is_separator_regex,
        separators=data.separators,
        preset_separators=data.preset_separators,
        metadata=data.metadata,
        request_context=request_context,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        postgres_session=postgres_session,
        redis_client=redis_client,
        model_registry=model_registry,
    )

    return JSONResponse(content=DocumentResponse(id=document_id).model_dump(), status_code=201)


@router.get(path=EndpointRoute.DOCUMENTS + "/{document_id}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Document)  # fmt: off
async def get_document(
    request: Request,
    document_id: Annotated[int, Path(ge=0, description="The document ID")],
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get a document by ID.
    """
    documents = await global_context.document_manager.get_documents(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document_id,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(content=documents[0].model_dump(), status_code=200)


@router.get(path=EndpointRoute.DOCUMENTS, dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_documents(
    request: Request,
    name: Annotated[str | None, StringConstraints(min_length=1, strip_whitespace=True)] = Query(default=None, description="Filter documents by name"),
    collection_id: int | None = Query(gt=0, default=None, description="Filter documents by collection ID"),
    limit: int = Query(ge=1, le=100, default=10, description="The number of documents to return"),
    offset: int = Query(default=0, description="The offset of the first document to return"),
    order_by: Literal["id", "name", "created"] = Query(default="id", description="The order by field to sort the documents by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the documents by."),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get all documents ID from a collection.
    """
    data = await global_context.document_manager.get_documents(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        collection_id=collection_id,
        document_name=name,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_direction=order_direction,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(content=Documents(data=data).model_dump(), status_code=200)


@router.delete(path=EndpointRoute.DOCUMENTS + "/{document_id}", dependencies=[Security(dependency=AccessController())], status_code=204)  # fmt: off
async def delete_document(
    request: Request,
    document_id: Annotated[int, Path(gt=0, description="The document ID")],
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Response:
    """
    Delete a document.
    """
    await global_context.document_manager.delete_document(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document_id,
        user_id=request_context.get().user_info.id,
    )

    return Response(status_code=204)


@router.post(path=EndpointRoute.DOCUMENTS + "/{document_id}/chunks", dependencies=[Security(dependency=AccessController())], status_code=201)  # fmt: off
async def create_document_chunks(
    request: Request,
    document_id: Annotated[int, Path(gt=0, description="The document ID")],
    body: CreateChunks,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    redis_client: AsyncRedis = Depends(get_redis_client),
    model_registry: ModelRegistry = Depends(get_model_registry),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Fill document with chunks.
    """
    chunk_ids = await global_context.document_manager.create_document_chunks(
        postgres_session=postgres_session,
        document_id=document_id,
        chunks=body.chunks,
        user_id=request_context.get().user_info.id,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        redis_client=redis_client,
        model_registry=model_registry,
        request_context=request_context,
    )

    return JSONResponse(content=ChunksResponse(document_id=document_id, ids=chunk_ids).model_dump(), status_code=201)


@router.delete(path=EndpointRoute.DOCUMENTS + "/{document_id}/chunks/{chunk_id}", dependencies=[Security(dependency=AccessController())], status_code=204)  # fmt: off
async def delete_document_chunk(
    request: Request,
    document_id: Annotated[int, Path(gt=0, description="The document ID")],
    chunk_id: Annotated[int, Path(ge=0, description="The chunk ID")],
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Response:
    """
    Delete a chunk of a document.
    """
    await global_context.document_manager.delete_document_chunk(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document_id,
        chunk_id=chunk_id,
        user_id=request_context.get().user_info.id,
    )
    return Response(status_code=204)


@router.get(path=EndpointRoute.DOCUMENTS + "/{document_id}/chunks", dependencies=[Security(dependency=AccessController())], status_code=200)  # fmt: off
async def get_document_chunks(
    request: Request,
    document_id: Annotated[int, Path(gt=0, description="The document ID")],
    limit: int = Query(ge=1, le=100, default=10, description="The number of chunks to return"),
    offset: int = Query(default=0, description="The offset of the first chunk to return"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get chunks of a document.
    """
    chunks = await global_context.document_manager.get_document_chunks(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document_id,
        limit=limit,
        offset=offset,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(content=Chunks(data=chunks).model_dump(), status_code=200)


@router.get(path=EndpointRoute.DOCUMENTS + "/{document_id}/chunks/{chunk_id}", dependencies=[Security(dependency=AccessController())],status_code=200)  # fmt: off
async def get_document_chunk(
    request: Request,
    document_id: Annotated[int, Path(gt=0, description="The document ID")],
    chunk_id: Annotated[int, Path(ge=0, description="The chunk ID")],
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get a chunk of a document.
    """
    chunks = await global_context.document_manager.get_document_chunk(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document_id,
        chunk_id=chunk_id,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(content=chunks[0].model_dump(), status_code=200)
