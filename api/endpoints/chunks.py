from uuid import UUID

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Path, Query, Request, Security
from sqlalchemy.ext.asyncio import AsyncSession

from api.helpers._accesscontroller import AccessController
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.schemas.chunks import Chunk, Chunks
from api.utils.context import global_context, request_context
from api.utils.dependencies import get_elasticsearch_client, get_elasticsearch_vector_store, get_postgres_session
from api.utils.exceptions import ChunkNotFoundException
from api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.CHUNKS.title()])


@router.get(path=EndpointRoute.CHUNKS + "/{document:path}/{chunk:path}", dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_chunk(
    request: Request,
    document: int = Path(description="The document ID"),
    chunk: int = Path(description="The chunk ID"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
) -> Chunk:
    """
    Get a chunk of a document.
    """
    if not global_context.document_manager:  # no vector store available
        raise ChunkNotFoundException()

    chunks = await global_context.document_manager.get_chunks(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        document_id=document,
        chunk_id=chunk,
        user_id=request_context.get().user_info.id,
    )

    return chunks[0]


@router.get(path=EndpointRoute.CHUNKS + "/{document}", dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_chunks(
    request: Request,
    document: int = Path(description="The document ID"),
    limit: int = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: int | UUID = Query(default=0, description="The offset of the first document to return"),
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
) -> Chunks:
    """
    Get chunks of a document.
    """
    if not global_context.document_manager:  # no vector store available
        data = []
    else:
        data = await global_context.document_manager.get_chunks(
            postgres_session=postgres_session,
            elasticsearch_vector_store=elasticsearch_vector_store,
            elasticsearch_client=elasticsearch_client,
            document_id=document,
            limit=limit,
            offset=offset,
            user_id=request_context.get().user_info.id,
        )

    return Chunks(data=data)
