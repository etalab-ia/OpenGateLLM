from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from itertools import batched
import logging
import time

from fastapi import HTTPException, UploadFile
from langchain_text_splitters import Language
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from api.clients.model import BaseModelProvider as ModelProvider
from api.clients.vector_store import BaseVectorStoreClient
from api.helpers.data.chunkers import NoSplitter, RecursiveCharacterTextSplitter
from api.helpers.models import ModelRegistry
from api.schemas.chunks import Chunk
from api.schemas.collections import Collection, CollectionVisibility
from api.schemas.core.context import RequestContext
from api.schemas.documents import Chunker, Document
from api.schemas.parse import ParsedDocument, ParsedDocumentOutputFormat
from api.schemas.search import Search
from api.sql.models import Collection as CollectionTable
from api.sql.models import Document as DocumentTable
from api.sql.models import Provider as ProviderTable
from api.sql.models import Router as RouterTable
from api.sql.models import User as UserTable
from api.utils.exceptions import (
    ChunkingFailedException,
    CollectionNotFoundException,
    DocumentNotFoundException,
    MasterNotAllowedException,
    VectorizationFailedException,
)
from api.utils.variables import ENDPOINT__EMBEDDINGS

from ._parsermanager import ParserManager

logger = logging.getLogger(__name__)


def check_dependencies(*, dependencies: list[str]) -> Callable:
    """
    Decorator to return a 400 error to the user if the endpoint calls a feature that requires an uninitialized dependency.
    """

    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            if "vector_store" in dependencies and not self.vector_store:
                raise HTTPException(status_code=400, detail="Feature not available: vector store is not initialized.")
            if "parser_manager" in dependencies and not self.parser_manager:
                raise HTTPException(status_code=400, detail="Feature not available: parser is not initialized.")

            return method(self, *args, **kwargs)

        return wrapper

    return decorator


class DocumentManager:
    BATCH_SIZE = 32

    def __init__(
        self,
        vector_store: BaseVectorStoreClient,
        vector_store_model: str,
        parser_manager: ParserManager,
    ) -> None:
        self.vector_store = vector_store
        self.vector_store_model = vector_store_model
        self.parser_manager = parser_manager

    @check_dependencies(dependencies=["vector_store"])
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

    @check_dependencies(dependencies=["vector_store"])
    async def delete_collection(self, postgres_session: AsyncSession, user_id: int, collection_id: int) -> None:
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
        await self.vector_store.delete_collection(collection_id=collection_id)

    @check_dependencies(dependencies=["vector_store"])
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

    @check_dependencies(dependencies=["vector_store"])
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

    @check_dependencies(dependencies=["vector_store"])
    async def create_document(
        self,
        postgres_session: AsyncSession,
        redis_client: AsyncRedis,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
        collection_id: int,
        document: ParsedDocument,
        chunker: Chunker,
        chunk_size: int,
        chunk_overlap: int,
        length_function: Callable,
        chunk_min_size: int,
        is_separator_regex: bool | None = None,
        separators: list[str] | None = None,
        preset_separators: Language | None = None,
        metadata: dict | None = None,
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

        try:
            # create index only when the first document is created to avoid increase shard with empty collections
            query = (
                select(ProviderTable.vector_size)
                .where(RouterTable.name == self.vector_store_model)
                .join(RouterTable, ProviderTable.router_id == RouterTable.id)
            ).limit(1)
            result = await postgres_session.execute(query)
            vector_size = result.scalar_one()

            await self.vector_store.create_collection(collection_id=collection_id, vector_size=vector_size)

        except Exception as e:
            logger.exception(msg=f"Error during collection ({collection_id}) creation: {e}", exc_info=True)
            raise VectorizationFailedException()
        try:
            chunks = self._split(
                document=document,
                chunker=chunker,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function,
                is_separator_regex=is_separator_regex,
                separators=separators,
                chunk_min_size=chunk_min_size,
                preset_separators=preset_separators,
                metadata=metadata,
            )
        except Exception as e:
            logger.exception(msg=f"Error during document splitting: {e}")
            raise ChunkingFailedException(detail=f"Chunking failed: {e}")

        document_name = document.data[0].metadata.document_name
        try:
            result = await postgres_session.execute(
                statement=insert(table=DocumentTable).values(name=document_name, collection_id=collection_id).returning(DocumentTable.id)
            )
        except Exception as e:
            if "foreign key constraint" in str(e).lower() or "fkey" in str(e).lower():
                raise CollectionNotFoundException(detail=f"Collection {collection_id} no longer exists")
            raise
        document_id = result.scalar_one()
        await postgres_session.commit()

        for chunk in chunks:
            chunk.metadata["collection_id"] = collection_id
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_created"] = round(time.time())
        try:
            await self._upsert(
                chunks=chunks,
                collection_id=collection_id,
                redis_client=redis_client,
                postgres_session=postgres_session,
                model_registry=model_registry,
                request_context=request_context,
            )
        except Exception as e:
            logger.exception(msg=f"Error during document creation: {e}")
            await self.delete_document(postgres_session=postgres_session, user_id=request_context.get().user_info.id, document_id=document_id)
            raise VectorizationFailedException(detail=f"Vectorization failed: {e}")

        return document_id

    @check_dependencies(dependencies=["vector_store"])
    async def get_documents(self, postgres_session: AsyncSession, user_id: int, collection_id: int | None = None, document_id: int | None = None, document_name: str | None = None, offset: int = 0, limit: int = 10) -> list[Document]:  # fmt: off
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
            document.chunks = await self.vector_store.get_chunk_count(collection_id=document.collection_id, document_id=document.id)

        return documents

    @check_dependencies(dependencies=["vector_store"])
    async def delete_document(self, postgres_session: AsyncSession, user_id: int, document_id: int) -> None:
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
        await self.vector_store.delete_document(collection_id=document.collection_id, document_id=document_id)

    @check_dependencies(dependencies=["vector_store"])
    async def get_chunks(
        self,
        postgres_session: AsyncSession,
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

        chunks = await self.vector_store.get_chunks(
            collection_id=document.collection_id,
            document_id=document_id,
            offset=offset,
            limit=limit,
            chunk_id=chunk_id,
        )

        return chunks

    @check_dependencies(dependencies=["parser_manager"])
    async def parse_file(
        self,
        file: UploadFile,
        output_format: ParsedDocumentOutputFormat | None = None,
        force_ocr: bool | None = None,
        page_range: str = "",
        paginate_output: bool | None = None,
        use_llm: bool | None = None,
    ) -> ParsedDocument:
        return await self.parser_manager.parse_file(
            file=file, output_format=output_format, force_ocr=force_ocr, page_range=page_range, paginate_output=paginate_output, use_llm=use_llm
        )

    @check_dependencies(dependencies=["vector_store"])
    async def search_chunks(
        self,
        postgres_session: AsyncSession,
        redis_client: AsyncRedis,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
        collection_ids: list[int],
        prompt: str,
        method: str,
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

        response = await self._create_embeddings(provider=provider, input_texts=[prompt], redis_client=redis_client)
        query_vector = response[0]

        searches = await self.vector_store.search(
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
        document: ParsedDocument,
        chunker: Chunker,
        chunk_size: int,
        chunk_min_size: int,
        chunk_overlap: int,
        length_function: Callable,
        separators: list[str] | None = None,
        is_separator_regex: bool | None = None,
        preset_separators: Language | None = None,
        metadata: dict | None = None,
    ) -> list[Chunk]:
        if chunker == Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER:
            chunker = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_min_size=chunk_min_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function,
                separators=separators,
                is_separator_regex=is_separator_regex,
                preset_separators=preset_separators,
                metadata=metadata,
            )
        else:  # Chunker.NoSplitter
            chunker = NoSplitter(chunk_min_size=chunk_min_size, preset_separators=preset_separators, metadata=metadata)

        chunks = chunker.split_document(document=document)

        return chunks

    async def _create_embeddings(self, provider: ModelProvider, input_texts: list[str], redis_client: AsyncRedis) -> list[float]:
        response = await provider.forward_request(
            method="POST",
            json={"input": input_texts, "model": self.vector_store_model, "encoding_format": "float"},
            endpoint=ENDPOINT__EMBEDDINGS,
            redis_client=redis_client,
        )
        return [vector["embedding"] for vector in response.json()["data"]]

    async def _upsert(
        self,
        chunks: list[Chunk],
        collection_id: int,
        redis_client: AsyncRedis,
        postgres_session: AsyncSession,
        model_registry: ModelRegistry,
        request_context: ContextVar[RequestContext],
    ) -> None:
        provider = await model_registry.get_model_provider(
            model=self.vector_store_model,
            endpoint=ENDPOINT__EMBEDDINGS,
            postgres_session=postgres_session,
            request_context=request_context,
            redis_client=redis_client,
        )

        batches = batched(iterable=chunks, n=self.BATCH_SIZE)
        for batch in batches:
            # create embeddings
            texts = [chunk.content for chunk in batch]
            embeddings = await self._create_embeddings(provider=provider, input_texts=texts, redis_client=redis_client)

            # insert chunks and vectors
            await self.vector_store.upsert(collection_id=collection_id, chunks=batch, embeddings=embeddings)
