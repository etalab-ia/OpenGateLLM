import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import gc
import logging
import math
import os
import random
import time
from typing import Any

from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from api.schemas.core.elasticsearch import ElasticsearchChunkFields, ElasticsearchIndexLanguage
from api.sql.models import Collection as CollectionTable
from api.sql.models import Document as DocumentTable

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%y:%m:%d %H:%M:%S")
logger = logging.getLogger(__name__)
logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)
# ============================== MODELS ==============================


class SourceChunk(BaseModel):
    id: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any]


class ElasticsearchCollectionInfo(BaseModel):
    id: int
    index: str
    chunks: int


# ============================== CLASSES ==============================


class Config(BaseSettings):
    postgres_url: str = Field(..., description="PostgreSQL connection URL.")
    source_es_url: str = Field(..., description="Source Elasticsearch connection URL.")
    source_es_username: str = Field(..., description="Source Elasticsearch username.")
    source_es_password: str = Field(..., description="Source Elasticsearch password.")
    destination_es_url: str = Field(..., description="Destination Elasticsearch connection URL.")
    destination_es_username: str = Field(..., description="Destination Elasticsearch username.")
    destination_es_password: str = Field(..., description="Destination Elasticsearch password.")
    destination_es_index_name: str = Field(default="opengatellm", description="Destination Elasticsearch index name.")
    destination_es_vector_size: int = Field(default=..., description="Destination Elasticsearch vector size.")
    destination_es_number_of_shards: int = Field(default=24, ge=1, description="Number of shards for the Elasticsearch index.", examples=[1])
    destination_es_number_of_replicas: int = Field(default=1, ge=0, description="Number of replicas for the Elasticsearch index.", examples=[1])
    destination_es_index_language: ElasticsearchIndexLanguage = Field(default=ElasticsearchIndexLanguage.FRENCH, description="Language of the Elasticsearch index.", examples=[ElasticsearchIndexLanguage.FRENCH.value])  # fmt: off


class PostgreSQL:
    def __init__(self, url: str):
        self.url: str = url

        self.engine: AsyncEngine = create_async_engine(self.url, echo=False, pool_size=20, max_overflow=0, pool_pre_ping=True)

    async def get_collections(self) -> list[str]:
        async with self.engine.connect() as connection:
            query = select(CollectionTable.id)
            result = await connection.execute(query)
            collections = [collection[0] for collection in result.fetchall()]

        return collections

    async def get_documents(self, collection_id: str):
        async with self.engine.connect() as connection:
            query = select(DocumentTable.id).where(DocumentTable.collection_id == collection_id)
            result = await connection.execute(query)

        return [document[0] for document in result.fetchall()]


class ElasticSearchSource:
    def __init__(self, url: str, username: str, password: str):
        self.url: str = url
        self.username: str = username
        self.password: str = password

        self.client = AsyncElasticsearch(hosts=url, basic_auth=(username, password), verify_certs=False, request_timeout=60, retry_on_timeout=True)

    async def get_collections(self) -> list[ElasticsearchCollectionInfo]:
        indices = await self.client.cat.indices(format="json")
        collections = []
        for index in indices:
            try:
                collection = ElasticsearchCollectionInfo(
                    id=int(index.get("index")), index=str(index.get("index")), chunks=int(index.get("docs.count", 0))
                )
                collections.append(collection)
            except (ValueError, TypeError):
                # Skip indices that don't have numeric names (not collection indices)
                continue

        collections = sorted(collections, key=lambda i: i.id)
        return collections

    async def get_chunks(self, collection_id: int, document_id: int, offset: int = 0, limit: int = 1000):
        query = {"bool": {"must": [{"terms": {"metadata.document_id": [document_id]}}]}}
        chunks = []
        results = await self.client.search(index=str(collection_id), query=query, size=limit, from_=offset)
        chunks = [
            ElasticsearchChunkFields(
                id=hit["_source"].get("id", 0),
                collection_id=collection_id,
                document_id=hit["_source"]["metadata"]["document_id"],
                content=hit["_source"]["content"],
                embedding=hit["_source"]["embedding"],
                document_name=hit["_source"]["metadata"].get("document_name"),
                created=hit["_source"]["metadata"].get("document_created", hit["_source"]["metadata"].get("document_created_at", int(time.time()))),
            )
            for hit in results["hits"]["hits"]
        ]

        chunks = sorted(chunks, key=lambda chunk: chunk.id)
        return chunks


class ElasticSearchDestination:
    def __init__(self, url: str, username: str, password: str, index_name: str):
        self.url: str = url
        self.username: str = username
        self.password: str = password
        self.index_name: str = index_name

        self.client = AsyncElasticsearch(hosts=url, basic_auth=(username, password), verify_certs=False, request_timeout=60, retry_on_timeout=True)

    async def create_index(self, index_language: ElasticsearchIndexLanguage, number_of_shards: int, number_of_replicas: int, vector_size: int):
        _es = ElasticsearchVectorStore(index_name=self.index_name)
        await _es.setup(
            client=self.client,
            index_language=index_language,
            number_of_shards=number_of_shards,
            number_of_replicas=number_of_replicas,
            vector_size=vector_size,
        )

    async def upsert_chunks(self, chunks: list[ElasticsearchChunkFields]):
        _es = ElasticsearchVectorStore(index_name=self.index_name)
        await _es.upsert(client=self.client, chunks=chunks)

    async def get_collections(self) -> list[ElasticsearchCollectionInfo]:
        results = {}
        after_key = None

        while True:
            body = {
                "size": 0,
                "aggs": {"collections": {"composite": {"size": 1000, "sources": [{"collection_id": {"terms": {"field": "collection_id"}}}]}}},
            }

            if after_key:
                body["aggs"]["collections"]["composite"]["after"] = after_key

            response = await self.client.search(index=self.index_name, body=body)

            buckets = response["aggregations"]["collections"]["buckets"]
            if not buckets:
                break

            for bucket in buckets:
                collection_id = bucket["key"]["collection_id"]
                doc_count = bucket["doc_count"]
                results[collection_id] = doc_count

            after_key = response["aggregations"]["collections"].get("after_key")
            if not after_key:
                break

        collections = [
            ElasticsearchCollectionInfo(
                id=collection_id,
                index=self.index_name,
                chunks=chunks,
            )
            for collection_id, chunks in results.items()
        ]

        collections = sorted(collections, key=lambda collection: collection.id)

        return collections

    async def get_chunks(self, collection_id: int, document_id: int, offset: int = 0, limit: int = 1000):
        results = await self.client.search(
            index=self.index_name,
            query={
                "bool": {
                    "must": [
                        {"term": {"collection_id": collection_id}},
                        {"term": {"document_id": document_id}},
                    ]
                }
            },
            size=limit,
            from_=offset,
        )
        chunks = [ElasticsearchChunkFields(**hit["_source"]) for hit in results["hits"]["hits"]]

        chunks = sorted(chunks, key=lambda chunk: chunk.id)
        return chunks


# ============================== FUNCTIONS ==============================


async def core_migration_logic(
    es_source: ElasticSearchSource,
    es_destination: ElasticSearchDestination,
    collections: list[ElasticsearchCollectionInfo],
):
    batch_chunks = []
    pid = os.getpid()
    total_collections = len(collections)

    for i, collection in enumerate(collections):
        collection_chunk_counter = 0
        scroll_id = None
        try:
            # Initialize scroll
            results = await es_source.client.search(index=collection.index, size=10000, scroll="5m", body={"query": {"match_all": {}}})
            scroll_id = results.get("_scroll_id")

            while True:
                hits = results["hits"]["hits"]
                collection_chunk_counter += len(hits)
                if not hits:
                    logger.info(f"[{pid}][{i}/{total_collections}][{collection.id}]\tfetched {collection_chunk_counter} chunks from source collection.")  # fmt: off
                    break

                chunks = [
                    ElasticsearchChunkFields(
                        id=hit["_source"].get("id", 0),
                        collection_id=collection.id,
                        document_id=hit["_source"]["metadata"]["document_id"],
                        content=hit["_source"]["content"],
                        embedding=hit["_source"]["embedding"],
                        document_name=hit["_source"]["metadata"].get("document_name"),
                        created=hit["_source"]["metadata"].get(
                            "document_created", hit["_source"]["metadata"].get("document_created_at", int(time.time()))
                        ),
                    )
                    for hit in hits
                ]
                collection_chunk_counter += len(chunks)
                batch_chunks.extend(chunks)

                if len(batch_chunks) > 10000:
                    logger.info(f"[{pid}]\t>>> upserting {len(batch_chunks)} chunks to destination collection...")
                    await es_destination.upsert_chunks(chunks=batch_chunks)
                    batch_chunks = []

                # Get next batch
                results = await es_source.client.scroll(scroll_id=scroll_id, scroll="5m")
                scroll_id = results.get("_scroll_id")

        except Exception as e:
            logger.exception(f"[{pid}][{i}/{total_collections}][{collection.id}]\terror processing during migration: {e}")
        finally:
            if scroll_id:
                try:
                    await es_source.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass

        gc.collect()

    if batch_chunks:
        logger.info(f"[{pid}]\t>>> upserting final batch of {len(batch_chunks)} chunks to destination collection...")
        await es_destination.upsert_chunks(chunks=batch_chunks)


def process_migration_batch(config: Config, batch: list[ElasticsearchCollectionInfo]):
    async def _run():
        es_source = ElasticSearchSource(url=config.source_es_url, username=config.source_es_username, password=config.source_es_password)
        es_destination = ElasticSearchDestination(
            url=config.destination_es_url,
            username=config.destination_es_username,
            password=config.destination_es_password,
            index_name=config.destination_es_index_name,
        )
        try:
            await core_migration_logic(es_source=es_source, es_destination=es_destination, collections=batch)
        except Exception as e:
            logger.exception(f"Error processing during migration: {e}")
            raise e
        finally:
            await es_source.client.close()
            await es_destination.client.close()

    return asyncio.run(_run())


async def migrate(config: Config, es_source: ElasticSearchSource, es_destination: ElasticSearchDestination, psql: PostgreSQL):
    # find collections to migrate
    collections = await psql.get_collections()
    logger.info(f"{len(collections)} collections are found in PostgreSQL database")

    source_collections = await es_source.get_collections()
    source_collections = [collection for collection in source_collections if collection.id in collections]
    logger.info(f"{len(source_collections)} collections are available in the source Elasticsearch cluster")

    destination_collections = await es_destination.get_collections()
    collections_to_migrate = []
    collections_to_skip = 0
    for source_collection in source_collections:
        migrated = False
        if source_collection.chunks == 0:
            collections_to_skip += 1
            continue
        for destination_collection in destination_collections:
            if source_collection.id == destination_collection.id and source_collection.chunks == destination_collection.chunks:
                migrated = True
                collections_to_skip += 1
                break
        if not migrated:
            collections_to_migrate.append(source_collection)
    logger.info(f"{len(collections_to_migrate)} collections will be migrated")
    logger.info(f"{collections_to_skip} collections will be skipped (already migrated)")

    if not collections_to_migrate:
        return

    # run migration
    num_processes = int(os.cpu_count() / 4 * 3) or 1

    chunk_size = math.ceil(len(collections_to_migrate) / num_processes)
    batches = [collections_to_migrate[i : i + chunk_size] for i in range(0, len(collections_to_migrate), chunk_size)]

    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(process_migration_batch, config, batch) for batch in batches]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.exception(f"Error processing during migration: {e}")
                raise e
            finally:
                future.cancel()


async def sanity_check(psql: PostgreSQL, es_source: ElasticSearchSource, es_destination: ElasticSearchDestination):
    chunk_counts, check_counter = 0, 0
    collections = await es_source.get_collections()
    for collection in collections:
        chunk_counts += collection.chunks

    random.shuffle(collections)
    max_checks = int(chunk_counts * 0.1)  # check 10% of the chunks
    logger.info(f"Starting sanity check, evaluating 10% of the source chunks ({max_checks} chunks)...")

    for collection in collections:
        documents = await psql.get_documents(collection_id=collection.id)
        if len(documents) == 0:
            continue

        if check_counter > max_checks:
            logger.info(f"Sanity check completed for {check_counter} chunks, stopping.")
            break

        documents = random.sample(documents, k=min(100, len(documents)))
        logger.info(f"[{check_counter}/{max_checks}]\tChecking\t{len(documents):>10} documents\tcollection {collection.id:>10}")
        for document_id in documents:
            source_chunks = await es_source.get_chunks(collection_id=collection.id, document_id=document_id)
            check_counter += len(source_chunks)
            destination_chunks = await es_destination.get_chunks(collection_id=collection.id, document_id=document_id)
            if len(source_chunks) != len(destination_chunks):
                logger.error(f"Collection {collection.id} has {len(source_chunks)} chunks in the source and {len(destination_chunks)} chunks in the destination (document {document_id})")  # fmt: off
                continue

            mapping = {obj.id: obj for obj in destination_chunks}
            zipped = [(a, mapping[a.id]) for a in source_chunks if a.id in mapping]
            if len(source_chunks) == 0:
                continue
            for source_chunk, destination_chunk in zipped:
                if source_chunk.id != destination_chunk.id:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same ID ({source_chunk.id} != {destination_chunk.id})")  # fmt: off
                if source_chunk.collection_id != destination_chunk.collection_id:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same collection ID ({source_chunk.collection_id} != {destination_chunk.collection_id})")  # fmt: off
                if source_chunk.document_id != destination_chunk.document_id:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same document ID ({source_chunk.document_id} != {destination_chunk.document_id})")  # fmt: off
                if source_chunk.content != destination_chunk.content:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same content)")  # fmt: off
                if source_chunk.embedding != destination_chunk.embedding:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same embedding")  # fmt: off
                if source_chunk.document_name != destination_chunk.document_name:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same document name ({source_chunk.document_name} != {destination_chunk.document_name})")  # fmt: off
                if source_chunk.created != destination_chunk.created:
                    logger.error(f"Chunk {source_chunk.id} of document {document_id} in collection {collection.id} has not same created ({source_chunk.created} != {destination_chunk.created})")  # fmt: off

    logger.info(f"Sanity check completed for {check_counter} chunks")


async def main():
    logger.info(f"Script started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")}\n")

    config = Config()

    psql = PostgreSQL(url=config.postgres_url)
    es_source = ElasticSearchSource(url=config.source_es_url, username=config.source_es_username, password=config.source_es_password)
    es_destination = ElasticSearchDestination(
        url=config.destination_es_url,
        username=config.destination_es_username,
        password=config.destination_es_password,
        index_name=config.destination_es_index_name,
    )

    assert await es_source.client.ping(), "Elasticsearch source connection error"
    assert await es_destination.client.ping(), "Elasticsearch destination connection error"

    await es_destination.create_index(
        index_language=ElasticsearchIndexLanguage.FRENCH,
        number_of_shards=config.destination_es_number_of_shards,
        number_of_replicas=config.destination_es_number_of_replicas,
        vector_size=config.destination_es_vector_size,
    )
    try:
        await migrate(config=config, es_source=es_source, es_destination=es_destination, psql=psql)
        logger.info("Migration successfully completed!")
        await sanity_check(psql=psql, es_source=es_source, es_destination=es_destination)
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
    finally:
        await psql.engine.dispose()
        await es_source.client.close()
        await es_destination.client.close()


# ============================== MAIN ==============================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nMigration interrupted by user (Ctrl+C). Exiting...")
