from contextvars import ContextVar
from datetime import datetime
from itertools import batched
import logging

from elasticsearch import AsyncElasticsearch
from fastapi import UploadFile
from langchain_text_splitters import Language
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelProvider as ModelProvider
from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.helpers.data.chunkers import NoSplitter, RecursiveCharacterTextSplitter
from api.helpers.models import ModelRegistry
from api.schemas.chunks import Chunk
from api.schemas.collections import Collection, CollectionVisibility
from api.schemas.core.context import RequestContext
from api.schemas.core.elasticsearch import ElasticsearchChunkFields
from api.schemas.core.models import RequestContent
from api.schemas.documents import Chunker, Document, InputChunkMetadata
from api.schemas.search import Search, SearchMethod
from api.sql.models import Collection as CollectionTable
from api.sql.models import Document as DocumentTable
from api.sql.models import User as UserTable
from api.utils.exceptions import (
    ChunkingFailedException,
    CollectionNotFoundException,
    DocumentNotFoundException,
    MasterNotAllowedException,
    ParsingDocumentFailedException,
    VectorizationFailedException,
)
from api.utils.variables import ENDPOINT__EMBEDDINGS

from ._parsermanager import ParserManager

logger = logging.getLogger(__name__)


class DocumentManager:
    BATCH_SIZE = 32

    def __init__(self, vector_store_model: str, parser_manager: ParserManager) -> None:
        self.vector_store_model = vector_store_model
        self.parser_manager = parser_manager

    async def create_collection(self, postgres_session: AsyncSession, user_id: int, name: str, visibility: CollectionVisibility, description: str | None = None) -> int:  # fmt: off
        if user_id == 0:
            raise MasterNotAllowedException(detail="Master user is not allowed to create collection.")

        query = (
            insert(table=CollectionTable)
            .values(name=name, user_id=user_id, visibility=visibility, description=description)
            .returning(CollectionTable.id)
        )
        result = await postgres_session.execute(statement=query)
        collection_id = result.scalar_one()
        await postgres_session.commit()

        return collection_id

    async def delete_collection(
        self,
        postgres_session: AsyncSession,
        elasticsearch_vector_store: ElasticsearchVectorStore,
        elasticsearch_client: AsyncElasticsearch,
        user_id: int,
        collection_id: int,
    ) -> None:
        # check if collection exists
        result = await postgres_session.execute(
            statement=select(CollectionTable.id).where(CollectionTable.id == collection_id).where(CollectionTable.user_id == user_id)
        )
        try:
            result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        # delete the collection
        await postgres_session.execute(statement=delete(table=CollectionTable).where(CollectionTable.id == collection_id))
        await postgres_session.commit()

        # delete the collection from vector store
        await elasticsearch_vector_store.delete_collection(client=elasticsearch_client, collection_id=collection_id)

    async def update_collection(self, postgres_session: AsyncSession, user_id: int, collection_id: int, name: str | None = None, visibility: CollectionVisibility | None = None, description: str | None = None) -> None:  # fmt: off
        # check if collection exists
        result = await postgres_session.execute(
            statement=select(CollectionTable)
            .join(target=UserTable, onclause=UserTable.id == CollectionTable.user_id)
            .where(CollectionTable.id == collection_id)
            .where(UserTable.id == user_id)
        )
        try:
            collection = result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        name = name if name is not None else collection.name
        visibility = visibility if visibility is not None else collection.visibility
        description = description if description is not None else collection.description

        await postgres_session.execute(
            statement=update(table=CollectionTable)
            .values(name=name, visibility=visibility, description=description)
            .where(CollectionTable.id == collection.id)
        )
        await postgres_session.commit()

    async def get_collections(
        self,
        postgres_session: AsyncSession,
        user_id: int,
        collection_id: int | None = None,
        collection_name: str | None = None,
        visibility: CollectionVisibility | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[Collection]:
        # Query basic collection data
        statement = (
            select(
                CollectionTable.id,
                CollectionTable.name,
                UserTable.name.label("owner"),
                CollectionTable.visibility,
                CollectionTable.description,
                func.count(distinct(DocumentTable.id)).label("documents"),
                cast(func.extract("epoch", CollectionTable.created), Integer).label("created"),
                cast(func.extract("epoch", CollectionTable.updated), Integer).label("updated"),
            )
            .outerjoin(DocumentTable, CollectionTable.id == DocumentTable.collection_id)
            .outerjoin(UserTable, CollectionTable.user_id == UserTable.id)
            .group_by(CollectionTable.id, UserTable.name)
            .offset(offset=offset)
            .order_by(CollectionTable.created.desc())
            .limit(limit=limit)
        )

        if collection_id:
            statement = statement.where(CollectionTable.id == collection_id)
        if collection_name:
            statement = statement.where(CollectionTable.name == collection_name)
        if visibility is None:
            statement = statement.where(or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
        else:
            statement = statement.where(CollectionTable.user_id == user_id, CollectionTable.visibility == visibility)

        result = await postgres_session.execute(statement=statement)
        collections = [Collection(**row._asdict()) for row in result.all()]

        if collection_id and len(collections) == 0:
            raise CollectionNotFoundException()

        return collections

    async def create_document(
        self,
        postgres_session: AsyncSession,
        redis_client: AsyncRedis,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
        elasticsearch_vector_store: ElasticsearchVectorStore,
        elasticsearch_client: AsyncElasticsearch,
        collection_id: int,
        file: UploadFile,
        metadata: InputChunkMetadata,
        chunker: Chunker,
        chunk_size: int,
        chunk_overlap: int,
        chunk_min_size: int,
        is_separator_regex: bool | None = None,
        separators: list[str] | None = None,
        preset_separators: Language | None = None,
    ) -> int:
        # check if collection exists and prepare document chunks in a single transaction
        result = await postgres_session.execute(
            statement=select(CollectionTable)
            .where(CollectionTable.id == collection_id)
            .where(CollectionTable.user_id == request_context.get().user_info.id)
        )
        try:
            result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        # get document name
        document_name = file.filename

        # parse the file
        try:
            content = await self.parser_manager.parse(file=file)
        except Exception as e:
            logger.exception(f"failed to parse {document_name} ({e}).")
            raise ParsingDocumentFailedException()

        # split the content into chunks
        chunks = self._split(
            content=content,
            chunker=chunker,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            is_separator_regex=is_separator_regex,
            separators=separators,
            chunk_min_size=chunk_min_size,
            preset_separators=preset_separators,
        )
        if len(chunks) == 0:
            raise ChunkingFailedException(detail="No chunks were extracted from the document.")

        # insert the document into the database
        try:
            result = await postgres_session.execute(
                statement=insert(table=DocumentTable)
                .values(
                    name=document_name,
                    collection_id=collection_id,
                )
                .returning(DocumentTable.id)
            )
        except Exception as e:
            if "foreign key constraint" in str(e).lower() or "fkey" in str(e).lower():
                raise CollectionNotFoundException(detail=f"Collection {collection_id} no longer exists")
            raise
        document_id = result.scalar_one()
        await postgres_session.commit()

        # index the chunks into the vector store
        try:
            await self._upsert(
                chunks=chunks,
                collection_id=collection_id,
                document_id=document_id,
                document_name=document_name,
                metadata=metadata,
                redis_client=redis_client,
                elasticsearch_vector_store=elasticsearch_vector_store,
                elasticsearch_client=elasticsearch_client,
                postgres_session=postgres_session,
                model_registry=model_registry,
                request_context=request_context,
            )
        except Exception as e:
            logger.exception(msg=f"Error during document creation: {e}")
            await self.delete_document(
                postgres_session=postgres_session,
                user_id=request_context.get().user_info.id,
                document_id=document_id,
                elasticsearch_vector_store=elasticsearch_vector_store,
                elasticsearch_client=elasticsearch_client,
            )
            raise VectorizationFailedException(detail=f"Vectorization failed: {e}")

        return document_id

    async def get_documents(self, postgres_session: AsyncSession, elasticsearch_vector_store: ElasticsearchVectorStore, elasticsearch_client: AsyncElasticsearch, user_id: int, collection_id: int | None = None, document_id: int | None = None, document_name: str | None = None, offset: int = 0, limit: int = 10) -> list[Document]:  # fmt: off
        statement = (
            select(
                DocumentTable.id,
                DocumentTable.name,
                DocumentTable.collection_id,
                cast(func.extract("epoch", DocumentTable.created), Integer).label("created"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .outerjoin(CollectionTable, DocumentTable.collection_id == CollectionTable.id)
            .where(or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
        )
        if collection_id:
            statement = statement.where(DocumentTable.collection_id == collection_id)
        if document_name:
            statement = statement.where(DocumentTable.name == document_name)
        if document_id:
            statement = statement.where(DocumentTable.id == document_id)

        result = await postgres_session.execute(statement=statement)
        documents = [Document(**row._asdict()) for row in result.all()]

        if document_id and len(documents) == 0:
            raise DocumentNotFoundException()

        # chunks count
        for document in documents:
            document.chunks = await elasticsearch_vector_store.get_chunk_count(
                client=elasticsearch_client,
                collection_id=document.collection_id,
                document_id=document.id,
            )

        return documents

    async def delete_document(
        self,
        postgres_session: AsyncSession,
        elasticsearch_vector_store: ElasticsearchVectorStore,
        elasticsearch_client: AsyncElasticsearch,
        user_id: int,
        document_id: int,
    ) -> None:
        # check if document exists
        result = await postgres_session.execute(
            statement=select(DocumentTable)
            .join(CollectionTable, DocumentTable.collection_id == CollectionTable.id)
            .where(DocumentTable.id == document_id)
            .where(CollectionTable.user_id == user_id)
        )
        try:
            document = result.scalar_one()
        except NoResultFound:
            raise DocumentNotFoundException()

        await postgres_session.execute(statement=delete(table=DocumentTable).where(DocumentTable.id == document_id))
        await postgres_session.commit()

        # delete the document from vector store
        await elasticsearch_vector_store.delete_document(client=elasticsearch_client, collection_id=document.collection_id, document_id=document_id)

    async def get_chunks(
        self,
        postgres_session: AsyncSession,
        elasticsearch_vector_store: ElasticsearchVectorStore,
        elasticsearch_client: AsyncElasticsearch,
        user_id: int,
        document_id: int,
        chunk_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> list[Chunk]:
        # check if document exists
        result = await postgres_session.execute(
            statement=select(DocumentTable)
            .join(CollectionTable, DocumentTable.collection_id == CollectionTable.id)
            .where(DocumentTable.id == document_id)
            .where(CollectionTable.user_id == user_id)
        )
        try:
            document = result.scalar_one()
        except NoResultFound:
            raise DocumentNotFoundException()

        chunks = await elasticsearch_vector_store.get_chunks(
            client=elasticsearch_client,
            collection_id=document.collection_id,
            document_id=document_id,
            offset=offset,
            limit=limit,
            chunk_id=chunk_id,
        )

        return chunks

    async def search_chunks(
        self,
        postgres_session: AsyncSession,
        elasticsearch_vector_store: ElasticsearchVectorStore,
        elasticsearch_client: AsyncElasticsearch,
        redis_client: AsyncRedis,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
        collection_ids: list[int],
        prompt: str,
        method: SearchMethod,
        limit: int,
        offset: int,
        rff_k: int,
        score_threshold: float = 0.0,
    ) -> list[Search]:
        # check if collections exist
        for collection_id in collection_ids:
            result = await postgres_session.execute(
                statement=select(CollectionTable)
                .where(CollectionTable.id == collection_id)
                .where(or_(CollectionTable.user_id == request_context.get().user_info.id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
            )
            try:
                result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException(detail=f"Collection {collection_id} not found.")

        if not collection_ids:
            return []  # to avoid a request to create a query vector

        provider = await model_registry.get_model_provider(
            model=self.vector_store_model,
            endpoint=ENDPOINT__EMBEDDINGS,
            postgres_session=postgres_session,
            redis_client=redis_client,
            request_context=request_context,
        )

        if method == SearchMethod.LEXICAL:
            query_vector = None
        else:
            response = await self._create_embeddings(provider=provider, input_texts=[prompt], redis_client=redis_client)
            query_vector = response[0]

        searches = await elasticsearch_vector_store.search(
            client=elasticsearch_client,
            method=method,
            collection_ids=collection_ids,
            query_prompt=prompt,
            query_vector=query_vector,
            limit=limit,
            offset=offset,
            rff_k=rff_k,
            score_threshold=score_threshold,
        )

        return searches

    @staticmethod
    def _split(
        content: str,
        chunker: Chunker,
        chunk_size: int,
        chunk_min_size: int,
        chunk_overlap: int,
        separators: list[str] | None = None,
        is_separator_regex: bool | None = None,
        preset_separators: Language | None = None,
    ) -> list[Chunk]:
        if chunker == Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER:
            chunker = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_min_size=chunk_min_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=separators,
                is_separator_regex=is_separator_regex,
                preset_separators=preset_separators,
            )
        else:  # Chunker.NoSplitter
            chunker = NoSplitter(chunk_min_size=chunk_min_size)

        chunks = chunker.split(content=content)

        return chunks

    async def _create_embeddings(self, provider: ModelProvider, input_texts: list[str], redis_client: AsyncRedis) -> list[float]:
        response = await provider.forward_request(
            request_content=RequestContent(
                method="POST",
                endpoint=ENDPOINT__EMBEDDINGS,
                json={"input": input_texts, "model": self.vector_store_model, "encoding_format": "float"},
                model=self.vector_store_model,
            ),
            redis_client=redis_client,
        )
        return [vector["embedding"] for vector in response.json()["data"]]

    async def _upsert(
        self,
        chunks: list[str],
        collection_id: int,
        document_id: int,
        document_name: str,
        metadata: InputChunkMetadata,
        redis_client: AsyncRedis,
        postgres_session: AsyncSession,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
        elasticsearch_vector_store: ElasticsearchVectorStore,
        elasticsearch_client: AsyncElasticsearch,
    ) -> None:
        provider = await model_registry.get_model_provider(
            model=self.vector_store_model,
            endpoint=ENDPOINT__EMBEDDINGS,
            postgres_session=postgres_session,
            request_context=request_context,
            redis_client=redis_client,
        )

        chunks_batches = batched(iterable=chunks, n=self.BATCH_SIZE)
        for chunks_batch in chunks_batches:
            # create embeddings
            embeddings = await self._create_embeddings(provider=provider, input_texts=chunks_batch, redis_client=redis_client)

            i = 0
            elasticsearch_chunks = list()
            for chunk, embedding in zip(chunks_batch, embeddings):
                elasticsearch_chunks.append(
                    ElasticsearchChunkFields(
                        id=i,
                        collection_id=collection_id,
                        document_id=document_id,
                        document_name=document_name,
                        content=chunk,
                        embedding=embedding,
                        created=datetime.now(),
                        source_ref=metadata.source_ref,
                        source_url=metadata.source_url,
                        source_title=metadata.source_title,
                        source_format=metadata.source_format,
                        source_author=metadata.source_author,
                        source_publisher=metadata.source_publisher,
                        source_priority=metadata.source_priority,
                        source_tags=metadata.source_tags,
                        source_date=metadata.source_date,
                    )
                )
                i += 1
            # insert chunks and vectors
            await elasticsearch_vector_store.upsert(client=elasticsearch_client, chunks=elasticsearch_chunks)
