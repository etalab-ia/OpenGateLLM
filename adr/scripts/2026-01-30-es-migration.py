import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import gc
import logging
import math
import os
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


class BufferedLogger:
    def __init__(self, collection_id: int, total_collections: int):
        self.buffer = []
        self.pid = os.getpid()
        self.collection_id = collection_id
        self.total_collections = total_collections

    def log(self, message: str, i: int):
        prefix = f"[{self.pid}][{self.collection_id}][{i}/{self.total_collections}]\t"
        msg = str(message)
        if msg.startswith("\n"):
            msg = msg.lstrip("\n")
        self.buffer.append(f"{prefix} {msg}")

    def flush(self, newline: bool = True):
        if self.buffer:
            logger.info("") if newline else None
            logger.info("\n".join(self.buffer))
            self.buffer = []


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
            logger.info(f"[{pid}][{i}/{total_collections}][{collection.id}]\tstarting to fetch chunks from source collection...")

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
            logger.exception(f"  Error processing during migration (collection {collection.index}): {e}")
        finally:
            # Clear scroll context
            if scroll_id:
                try:
                    await es_source.client.clear_scroll(scroll_id=scroll_id)
                except Exception:
                    pass  # Ignore errors when clearing scroll

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
    migration_collections = []
    for source_collection in source_collections:
        migrated = False
        for destination_collection in destination_collections:
            if source_collection.id == destination_collection.id and source_collection.chunks == destination_collection.chunks:
                migrated = True
                break
        if not migrated:
            migration_collections.append(source_collection)
    logger.info(f"{len(migration_collections)} collections will be migrated")

    # run migration
    num_processes = int(os.cpu_count() / 4 * 3) or 1

    chunk_size = math.ceil(len(migration_collections) / num_processes)
    batches = [migration_collections[i : i + chunk_size] for i in range(0, len(migration_collections), chunk_size)]

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
        logger.info("\nMigration successfully completed!\n")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
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
