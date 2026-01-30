import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from enum import Enum
import gc
import math
import os
import re
import time
from typing import Any, Literal

from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from pydantic import BaseModel, Field
import sqlalchemy
from sqlalchemy import CursorResult
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# ============================== MODELS ==============================


class OldDocumentSourceModel(BaseModel):
    id: int
    content: str
    embedding: list[float]
    metadata: dict[str, Any]  # Contains document_name (str), page (int), collection_id (int), document_id (int), document_created (int / timestamp)


class NewDocumentSourceModel(BaseModel):
    id: int
    collection_id: int
    document_id: int
    document_name: str | None = None
    content: str
    embedding: list[float]
    created: int | None = None  # timestamp / date
    source_ref: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    source_author: str | None = None
    source_publisher: str | None = None
    source_priority: int | None = None
    source_tags: list[str] | None = None
    source_date: int | None = None  # timestamp / date


class OldDocumentModel(BaseModel):
    index: Literal["opengatellm"] = Field(alias="_index")
    source: OldDocumentSourceModel = Field(alias="_source")

    @property
    def _index(self):
        return self.index

    @property
    def _source(self):
        return self.source

    def __repr__(self):
        return str(self.model_dump(by_alias=True))


class NewDocumentModel(BaseModel):
    index: Literal["opengatellm"] = Field(alias="_index")
    source: NewDocumentSourceModel = Field(alias="_source")

    @property
    def _index(self):
        return self.index

    @property
    def _source(self):
        return self.source

    def __repr__(self):
        return str(self.model_dump(by_alias=True))


class IndexInfoModel(BaseModel):
    uuid: str
    health: str
    status: str
    index: str
    docs_quantity: int
    storage_size: int


class ElasticsearchIndexLanguage(str, Enum):
    """
    The language of the Elasticsearch index, composed by the value, the stopwords and the stemmer.
    For more information about stemmer, see https://www.elastic.co/docs/reference/text-analysis/analysis-stemmer-tokenfilter#analysis-stemmer-tokenfilter-configure-parms.
    """

    ENGLISH = ("english", "_english_", "light_english")
    FRENCH = ("french", "_french_", "light_french")
    GERMAN = ("german", "_german_", "light_german")
    ITALIAN = ("italian", "_italian_", "light_italian")
    PORTUGUESE = ("portuguese", "_portuguese_", "light_portuguese")
    SPANISH = ("spanish", "_spanish_", "light_spanish")
    SWEDISH = ("swedish", "_swedish_", "light_swedish")

    def __new__(cls, value, stopwords, stemmer):
        if not isinstance(value, str):
            raise TypeError(f"Enum values must be strings (got {type(value).__name__})")
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.stopwords = stopwords
        obj.stemmer = stemmer

        return obj


# ============================== CLASSES ==============================


class Config:
    OLD_ES_URL: str
    OLD_ES_USERNAME: str
    OLD_ES_PASSWORD: str
    NEW_ES_URL: str
    NEW_ES_USERNAME: str
    NEW_ES_PASSWORD: str

    @classmethod
    def setup(cls, silent: bool = False):
        if not silent:
            print("=" * 20 + " CONFIGURATION " + "=" * 20)
            print("Loading environment variables from .env file...")
        load_dotenv()

        # PostgreSQL
        cls.POSTGRES_USER = os.getenv("POSTGRES_USER")
        cls.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
        cls.POSTGRES_HOST = os.getenv("POSTGRES_HOST")
        cls.POSTGRES_PORT = os.getenv("POSTGRES_PORT")
        cls.POSTGRES_DB = os.getenv("POSTGRES_DB")
        # Elasticsearch
        cls.SOURCE_ES_URL = os.getenv("SOURCE_ES_URL")
        cls.SOURCE_ES_USERNAME = os.getenv("SOURCE_ES_USERNAME")
        cls.SOURCE_ES_PASSWORD = os.getenv("SOURCE_ES_PASSWORD")
        cls.DESTINATION_ES_URL = os.getenv("DESTINATION_ES_URL")
        cls.DESTINATION_ES_USERNAME = os.getenv("DESTINATION_ES_USERNAME")
        cls.DESTINATION_ES_PASSWORD = os.getenv("DESTINATION_ES_PASSWORD")

        missing = [
            name
            for name in (
                # PostgreSQL
                "POSTGRES_USER",
                "POSTGRES_PASSWORD",
                "POSTGRES_HOST",
                "POSTGRES_PORT",
                "POSTGRES_DB",
                # Elasticsearch
                "SOURCE_ES_URL",
                "SOURCE_ES_USERNAME",
                "SOURCE_ES_PASSWORD",
                "DESTINATION_ES_URL",
                "DESTINATION_ES_USERNAME",
                "DESTINATION_ES_PASSWORD",
            )
            if not getattr(cls, name)
        ]
        if missing:
            raise OSError(f"Missing required environment variables: {", ".join(missing)}")
        if not silent:
            print("Environment variables loaded successfully")
            print("=" * 20 + " CONFIGURATION " + "=" * 20 + "\n")


class Utils:
    @classmethod
    def convert_size_to_bytes(cls, size_str: str) -> int:
        size_str = size_str.strip().upper()
        size_mapping = {
            "B": 1,
            "KB": 1000,
            "MB": 1000**2,
            "GB": 1000**3,
            "TB": 1000**4,
        }
        match = re.match(r"([\d.]+)([A-Z]+)", size_str)
        if match:
            size_value = float(match.group(1))
            size_unit = match.group(2)
            return int(size_value * size_mapping.get(size_unit, 1))
        return 0

    @classmethod
    def convert_size_to_readable(cls, size_in_bytes: int) -> str:
        if size_in_bytes < 1000:
            return f"{size_in_bytes} B"
        elif size_in_bytes < 1000**2:
            return f"{size_in_bytes / 1000:.2f} KB"
        elif size_in_bytes < 1000**3:
            return f"{size_in_bytes / (1000**2):.2f} MB"
        elif size_in_bytes < 1000**4:
            return f"{size_in_bytes / (1000**3):.2f} GB"
        else:
            return f"{size_in_bytes / (1000**4):.2f} TB"

    @classmethod
    def sum_field_from_indices(cls, indices: list[IndexInfoModel], field_name: str) -> int:
        total = 0
        for index in indices:
            total += getattr(index, field_name)
        return total

    @classmethod
    def fmt_timestamp(cls, ts: float):
        if not ts:
            return "N/A"
        return datetime.fromtimestamp(ts, tz=UTC).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    @classmethod
    def fmt_duration(cls, start, end, full: bool = True):
        if not start or not end:
            return "N/A"
        total = end - start
        hours, rem = divmod(int(total), 3600)
        minutes, seconds = divmod(rem, 60)
        if not full:
            return f"{total:.3f}s"
        return f"{total:.2f}s ({hours}h {minutes}m {seconds}s)"


class PSQL:
    engine: AsyncEngine | None = None
    all_collections: list[str] = []
    common_collections: list[str] = []
    different_collections: list[str] = []

    @staticmethod
    def _get_postgres_dsn() -> str:
        return f"postgresql+asyncpg://{Config.POSTGRES_USER}:{Config.POSTGRES_PASSWORD}@{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/{Config.POSTGRES_DB}"

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        url: str = cls._get_postgres_dsn()
        if not cls.engine:
            cls.engine = create_async_engine(url, echo=False)
        return cls.engine

    @classmethod
    async def healthcheck(cls) -> bool:
        print("=" * 20 + " POSTGRESQL " + "=" * 20)
        try:
            print("Checking connection to PostgreSQL database...")
            engine = cls.get_engine()
            async with engine.connect() as connection:
                check: CursorResult[Any] = await connection.execute(sqlalchemy.text("SELECT 1"))
                name: str = connection.engine.url.database
                if check.scalar_one() and name:
                    print(f"Successfully connected to the {name} database")
                    print("=" * 20 + " POSTGRESQL " + "=" * 20 + "\n")
                    return True
                else:
                    raise ConnectionError("Unable to connect to PostgreSQL database")
        except Exception as e:
            raise ConnectionError(f"Database connection error: {e}")

    @classmethod
    async def close(cls):
        if cls.engine:
            await cls.engine.dispose()
            cls.engine = None

    @classmethod
    async def get_collections(cls, engine: AsyncEngine) -> list[str]:
        collections: list[str] = []
        async with engine.connect() as connection:
            result: CursorResult[Any] = await connection.execute(sqlalchemy.text("SELECT id FROM collection ORDER BY id ASC"))
            rows = result.fetchall()
            collections = [str(row.id) for row in rows]
        print(f"Found {len(collections)} collections in PostgreSQL database")
        cls.all_collections = collections
        return collections


class ES:
    source: AsyncElasticsearch | None = None
    destination: AsyncElasticsearch | None = None
    migrated_indices: list[IndexInfoModel] = []
    skipped_indices: list[IndexInfoModel] = []
    error_indices: list[IndexInfoModel] = []
    retry_count: int = 0
    start_time: float = time.time()
    end_time: float = 0

    @classmethod
    async def get_source_client(cls) -> AsyncElasticsearch:
        if not cls.source:
            cls.source = AsyncElasticsearch(
                Config.SOURCE_ES_URL,
                basic_auth=(Config.SOURCE_ES_USERNAME, Config.SOURCE_ES_PASSWORD),
                verify_certs=False,
                request_timeout=60,
                retry_on_timeout=True,
            )
        return cls.source

    @classmethod
    async def get_destination_client(cls) -> AsyncElasticsearch:
        if not cls.destination:
            cls.destination = AsyncElasticsearch(
                Config.DESTINATION_ES_URL,
                basic_auth=(Config.DESTINATION_ES_USERNAME, Config.DESTINATION_ES_PASSWORD),
                verify_certs=False,
                request_timeout=60,
                retry_on_timeout=True,
            )
        return cls.destination

    @classmethod
    async def healthcheck(cls) -> bool:
        print("=" * 20 + " ELASTICSEARCH " + "=" * 20)
        try:
            print("Checking connection to source Elasticsearch cluster...")
            source = await cls.get_source_client()
            if not await source.ping():
                raise ConnectionError("Unable to connect to source Elasticsearch cluster")
            print("Successfully connected to source Elasticsearch cluster")

            print("Checking connection to destination Elasticsearch cluster...")
            dest = await cls.get_destination_client()
            if not await dest.ping():
                raise ConnectionError("Unable to connect to destination Elasticsearch cluster")
            print("Successfully connected to destination Elasticsearch cluster")

            print("Successfully connected to both Elasticsearch clusters")
            print("=" * 20 + " ELASTICSEARCH " + "=" * 20 + "\n")
            return True

        except Exception as e:
            raise ConnectionError(f"Elasticsearch connection error: {e}")

    @classmethod
    async def close(cls):
        if cls.source:
            await cls.source.close()
            cls.source = None
        if cls.destination:
            await cls.destination.close()
            cls.destination = None
            # Update the NewDocumentSourceModel class according to the new mapping in the create_index method of the ES class

    @classmethod
    async def create_index(
        cls,
        client: AsyncElasticsearch,
        index_name: str,
        index_language: ElasticsearchIndexLanguage,
        number_of_shards: int = 5,
        number_of_replicas: int = 1,
        vector_size: int = 1024,
    ) -> None:
        print(f"Creating {index_name} index...")
        if await client.indices.exists(index=index_name):
            print(f"Index {index_name} already exists")
            return

        settings = {
            "number_of_shards": number_of_shards,
            "number_of_replicas": number_of_replicas,
            "similarity": {"default": {"type": "BM25"}},
            "analysis": {
                "filter": {
                    "stop": {"type": "stop", "stopwords": index_language.stopwords},
                    "stemmer": {"type": "stemmer", "language": index_language.stemmer},
                },
                "analyzer": {
                    "content_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "stop", "stemmer"],
                    },
                },
            },
        }
        mappings = {
            "properties": {
                # chunk core properties
                "id": {"type": "integer"},
                "collection_id": {"type": "integer"},
                "document_id": {"type": "integer"},
                "document_name": {"type": "keyword"},  # can be overridden by user
                "embedding": {"type": "dense_vector", "dims": vector_size, "index": True, "similarity": "cosine"},
                "content": {"type": "text", "analyzer": "content_analyzer"},
                "created": {"type": "date"},
                # document source properties
                "source_ref": {"type": "keyword"},
                "source_url": {"type": "keyword"},
                "source_title": {"type": "keyword"},
                "source_author": {"type": "keyword"},
                "source_publisher": {"type": "keyword"},
                "source_priority": {"type": "integer"},
                "source_tags": {"type": "keyword"},  # array of keywords
                "source_date": {"type": "date"},
            },
        }

        print(f"Index {index_name} does not exist. Creating...")
        await client.indices.create(index=index_name, mappings=mappings, settings=settings)
        print(f"Index {index_name} created successfully")

    @classmethod
    async def get_indices(cls, client: AsyncElasticsearch, client_type: str = "source") -> list[IndexInfoModel]:
        indices = await client.cat.indices(format="json")
        indices: list[IndexInfoModel] = [
            IndexInfoModel(
                uuid=index.get("uuid"),
                health=index.get("health"),
                status=index.get("status"),
                index=index.get("index"),
                docs_quantity=int(index.get("docs.count")),
                storage_size=Utils.convert_size_to_bytes(index.get("store.size")),
            )
            for index in indices
        ]
        sorted_indices = sorted(indices, key=lambda i: i.index)
        print(f"Found {len(sorted_indices)} indices in {client_type} Elasticsearch cluster")
        return sorted_indices

    @classmethod
    async def fetch_documents_from_index(cls, client: AsyncElasticsearch, index_name: str):
        documents = []
        body = {"size": 10000, "query": {"match_all": {}}}
        response = await client.search(index=index_name, body=body, scroll="1m")
        scroll_id = response["_scroll_id"]
        hits = response["hits"]["hits"]
        documents.extend(hits)

        while len(hits) > 0:
            response = await client.scroll(scroll_id=scroll_id, scroll="1m")
            scroll_id = response["_scroll_id"]
            hits = response["hits"]["hits"]
            documents.extend(hits)

        await client.clear_scroll(scroll_id=scroll_id)
        return documents

    @classmethod
    async def reformat_document(cls, old_document: OldDocumentModel) -> NewDocumentModel:
        old_source = old_document.source
        metadata = old_source.metadata.copy()
        collection_id = metadata.get("collection_id")
        document_id = metadata.get("document_id")
        document_name = metadata.get("document_name")
        document_created = metadata.get("document_created")

        new_source = NewDocumentSourceModel(
            id=old_source.id,
            collection_id=collection_id,
            document_id=document_id,
            document_name=document_name,
            created=document_created,
            content=old_source.content,
            embedding=old_source.embedding,
            source_ref=None,
            source_url=None,
            source_title=None,
            source_author=None,
            source_publisher=None,
            source_priority=None,
            source_tags=None,
            source_date=None,
        )
        new_document = NewDocumentModel(_index="opengatellm", _source=new_source)

        return new_document

    @classmethod
    def print_pre_migration_summary(cls, collections: list[str], source_indices: list[IndexInfoModel], title: str = "PRE MIGRATION SUMMARY REPORT"):
        cls.start_time = time.time()
        cls.source_indices = source_indices  # Store for post-migration summary
        common_indices = [i for i in source_indices if i.index in collections]
        different_indices = [i for i in source_indices if i.index not in collections]

        print("\n" + "=" * 20 + f" {title} " + "=" * 20)
        print("==========> INDICES")
        print(f"Total:\t\t {len(source_indices)}")
        print(f"Identical:\t {len(common_indices)}")
        print(f"Different:\t {len(different_indices)}")
        print("==========> DOCUMENTS")
        print(f"Total:\t\t {Utils.sum_field_from_indices(source_indices, "docs_quantity")}")
        print(f"Kept:\t\t {Utils.sum_field_from_indices(common_indices, "docs_quantity")}")
        print(f"Skipped:\t {Utils.sum_field_from_indices(different_indices, "docs_quantity")}")
        print("==========> STORAGE")
        print(f"Total:\t\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(source_indices, "storage_size"))}")
        print(f"Kept:\t\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(common_indices, "storage_size"))}")
        print(f"Skipped:\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(different_indices, "storage_size"))}")
        print("=" * 20 + "=" * (len(title) + 2) + "=" * 20 + "\n")

    @classmethod
    def print_post_migration_summary(cls, title: str = "POST MIGRATION SUMMARY REPORT"):
        cls.end_time = time.time()

        print("\n" + "=" * 20 + f" {title} " + "=" * 20)
        print("==========> DURATION")
        print(f"Start:\t\t {Utils.fmt_timestamp(cls.start_time)}")
        print(f"End:\t\t {Utils.fmt_timestamp(cls.end_time)}")
        print(f"Total:\t\t {Utils.fmt_duration(cls.start_time, cls.end_time)}")
        print(f"Retries:\t {cls.retry_count}")
        print("==========> INDICES")
        print(f"Total:\t\t {len(cls.source_indices)}")
        print(f"Migrated:\t {len(cls.migrated_indices)}")
        print(f"Skipped:\t {len(cls.skipped_indices)}")
        print(f"Errors:\t\t {len(cls.error_indices)}")
        print("==========> DOCUMENTS")
        print(f"Total:\t\t {Utils.sum_field_from_indices(cls.source_indices, "docs_quantity")}")
        print(f"Migrated:\t {Utils.sum_field_from_indices(cls.migrated_indices, "docs_quantity")}")
        print(f"Skipped:\t {Utils.sum_field_from_indices(cls.skipped_indices, "docs_quantity")}")
        print(f"Errors:\t\t {Utils.sum_field_from_indices(cls.error_indices, "docs_quantity")}")
        print("==========> STORAGE")
        print(f"Total:\t\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(cls.source_indices, "storage_size"))}")
        print(f"Migrated:\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(cls.migrated_indices, "storage_size"))}")
        print(f"Skipped:\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(cls.skipped_indices, "storage_size"))}")
        print(f"Errors:\t\t {Utils.convert_size_to_readable(Utils.sum_field_from_indices(cls.error_indices, "storage_size"))}")
        print("=" * 20 + "=" * (len(title) + 2) + "=" * 20 + "\n")


async def initialize():
    Config.setup()
    try:
        await PSQL.healthcheck()
        await ES.healthcheck()
    finally:
        await PSQL.close()
        await ES.close()


class BufferedLogger:
    def __init__(self, index_name: str):
        self.buffer = []
        self.pid = os.getpid()
        self.index_name = index_name

    def log(self, message):
        prefix = f"[{self.pid}][{self.index_name}]\t"
        msg = str(message)
        if msg.startswith("\n"):
            msg = msg.lstrip("\n")
        self.buffer.append(f"{prefix} {msg}")

    def flush(self, newline: bool = True):
        if self.buffer:
            print("") if newline else None
            print("\n".join(self.buffer))
            self.buffer = []


async def core_migration_logic(
    es_source: AsyncElasticsearch, es_destination: AsyncElasticsearch, collections: list[str], source_indices: list[IndexInfoModel]
):
    print(f"\nStarting migration for {len(source_indices)} ES indices...")
    for index in source_indices:
        index_name: str = index.index

        logger = BufferedLogger(index_name)
        logger.log(f"Processing index: {index_name} with {index.docs_quantity} documents...")

        try:
            if index_name in collections:
                logger.log(f"  Collection {index_name} exists in PostgreSQL")
                if index in ES.migrated_indices:
                    logger.log(f"  Index {index_name} has already been migrated. Skipping...")
                    ES.skipped_indices.append(index)
                    logger.flush()
                    continue
                logger.log(f"  Fetching {index.docs_quantity} documents ({Utils.convert_size_to_readable(index.storage_size)}) from source index...")
                start = time.time()
                docs = await ES.fetch_documents_from_index(client=es_source, index_name=index_name)
                end = time.time()
                logger.log(f"  Fetched {len(docs)} documents from source index ({Utils.fmt_duration(start, end, full=False)})")

                actions = []
                skipped_in_this_index: int = 0
                for doc in docs:
                    try:
                        source = doc.get("_source") if isinstance(doc, dict) else None
                        if not source:
                            raise ValueError("Document source is missing")

                        source_doc: OldDocumentModel = OldDocumentModel(
                            _index="opengatellm",
                            # Should I keep the same id between different migration run to optimize? - YES
                            _source=OldDocumentSourceModel(
                                id=source.get("id"),
                                content=source.get("content"),
                                embedding=source.get("embedding"),
                                metadata=source.get("metadata", {}),
                            ),
                        )

                        new_doc = await ES.reformat_document(old_document=source_doc)
                        action = new_doc.model_dump(by_alias=True)
                        action["_index"] = "opengatellm"
                        actions.append(action)
                    except Exception as e:
                        logger.log(f"  Failed to reformat document in {index_name}: {e}")
                        skipped_in_this_index += 1

                if actions:
                    logger.log(f"  Inserting {len(actions)} documents into destination index (skipped {skipped_in_this_index} documents)...")
                    start = time.time()
                    success_count, errors = await async_bulk(es_destination, actions)
                    end = time.time()
                    logger.log(f"  Inserted {success_count} documents into destination index ({Utils.fmt_duration(start, end, full=False)})")

                    if errors:
                        logger.log(f"  Encountered {len(errors)} errors during bulk insert")
                        logger.log(f"  {errors}")

                ES.migrated_indices.append(index)

            else:
                logger.log(f"  Collection {index_name} does not exist in PostgreSQL. Skipping migration")
                ES.skipped_indices.append(index)
                logger.flush()
                continue

        except Exception as e:
            logger.log(f"  Error processing index {index_name}: {e}")
            ES.error_indices.append(index)
            logger.flush()
            continue

        logger.flush()
        gc.collect()


def process_migration_batch(collections, indices, config_env):
    # Re-setup environment in worker
    os.environ.update(config_env)

    async def _run():
        Config.setup(silent=True)

        # Reset local tracking
        ES.migrated_indices = []
        ES.skipped_indices = []
        ES.error_indices = []

        try:
            es_source = await ES.get_source_client()
            es_destination = await ES.get_destination_client()

            await core_migration_logic(es_source, es_destination, collections, indices)
        finally:
            await ES.close()
        return ES.migrated_indices, ES.skipped_indices, ES.error_indices

    return asyncio.run(_run())


def chunk_list(data, num_chunks):
    chunk_size = math.ceil(len(data) / num_chunks)
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


async def migrate():
    es_source = await ES.get_source_client()
    es_destination = await ES.get_destination_client()
    psql_engine = PSQL.get_engine()

    await ES.create_index(client=es_destination, index_name="opengatellm", index_language=ElasticsearchIndexLanguage.FRENCH, vector_size=1024)
    collections: list[str] = await PSQL.get_collections(engine=psql_engine)
    source_indices = await ES.get_indices(client=es_source, client_type="source")

    ES.print_pre_migration_summary(collections, source_indices)

    # Initial Migration Run with Multiprocessing

    # Prepare chunks
    num_processes = int(os.cpu_count() / 4 * 3) or 1
    print(f"\nStarting parallel migration with {num_processes} processes...")
    indices_chunks = chunk_list(source_indices, num_processes)
    config_env = dict(os.environ)

    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(process_migration_batch, collections, chunk, config_env) for chunk in indices_chunks if chunk]

        for future in futures:
            try:
                migrated, skipped, errors = future.result()
                ES.migrated_indices.extend(migrated)
                ES.skipped_indices.extend(skipped)
                ES.error_indices.extend(errors)
            except Exception as e:
                print(f"Worker process failed: {e}")

    max_retries = 20
    while ES.error_indices and ES.retry_count < max_retries:
        ES.retry_count += 1
        print("\n" + "=" * 60)
        print(f"RETRY ATTEMPT {ES.retry_count}/{max_retries}")
        print(f"Retrying migration for {len(ES.error_indices)} indices that encountered errors...")
        print("=" * 60 + "\n")

        indices_to_retry = ES.error_indices[:]
        ES.error_indices = []

        await core_migration_logic(es_source, es_destination, collections, indices_to_retry)

    ES.print_post_migration_summary()


async def main():
    try:
        print(f"Script started at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")}\n")
        await initialize()
        await migrate()
        print("\nMigration successfully completed!\n")
    finally:
        await PSQL.close()
        await ES.close()


# NOTE - No check of env var when using ES and PSQL classes
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user (Ctrl+C). Exiting...")
