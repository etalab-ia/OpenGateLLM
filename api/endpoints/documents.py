from contextvars import ContextVar
from typing import Annotated
from uuid import UUID

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Path, Query, Request, Response, Security
from fastapi.responses import JSONResponse
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers.models import ModelRegistry
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
from api.utils.exceptions import CollectionNotFoundException, DocumentNotFoundException
from api.utils.variables import ENDPOINT__DOCUMENTS, ROUTER__DOCUMENTS

router = APIRouter(prefix="/v1", tags=[ROUTER__DOCUMENTS.title()])


@router.post(path=ENDPOINT__DOCUMENTS, status_code=201, dependencies=[Security(dependency=AccessController())], response_model=DocumentResponse)
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
    Parse a file and create a document.
    """
    if not global_context.document_manager:  # no vector store available
        raise CollectionNotFoundException()

    document_id = await global_context.document_manager.create_document(
        request_context=request_context,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        postgres_session=postgres_session,
        redis_client=redis_client,
        model_registry=model_registry,
        collection_id=data.collection,
        file=data.file,
        chunker=data.chunker,
        chunk_size=data.chunk_size,
        chunk_min_size=data.chunk_min_size,
        chunk_overlap=data.chunk_overlap,
        is_separator_regex=data.is_separator_regex,
        separators=data.separators,
        preset_separators=data.preset_separators,
        metadata=data.metadata,
    )

    return JSONResponse(content=DocumentResponse(id=document_id).model_dump(), status_code=201)


@router.get(
    path=ENDPOINT__DOCUMENTS + "/{document}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Document,
)
async def get_document(
    request: Request,
    document: int = Path(description="The document ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get a document by ID.
    """
    if not global_context.document_manager:  # no vector store available
        raise DocumentNotFoundException()

    documents = await global_context.document_manager.get_documents(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(content=documents[0].model_dump(), status_code=200)


@router.get(path=ENDPOINT__DOCUMENTS, dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_documents(
    request: Request,
    name: str | None = Query(default=None, description="Filter documents by name."),
    collection: int | None = Query(default=None, description="Filter documents by collection ID"),
    limit: int | None = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: int | UUID = Query(default=0, description="The offset of the first document to return"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> JSONResponse:
    """
    Get all documents ID from a collection.
    """

    if not global_context.document_manager:  # no vector store available
        if collection:
            raise CollectionNotFoundException()

        return Documents(data=[])

    data = await global_context.document_manager.get_documents(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        collection_id=collection,
        document_name=name,
        limit=limit,
        offset=offset,
        user_id=request_context.get().user_info.id,
    )

    return JSONResponse(content=Documents(data=data).model_dump(), status_code=200)


@router.delete(path=ENDPOINT__DOCUMENTS + "/{document}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_document(
    request: Request,
    document: int = Path(description="The document ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
) -> Response:
    """
    Delete a document.
    """
    if not global_context.document_manager:  # no vector store available
        raise DocumentNotFoundException()

    await global_context.document_manager.delete_document(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document,
        user_id=request_context.get().user_info.id,
    )

    return Response(status_code=204)
