"""Migrate RAG metadata from an OpenGateLLM Postgres database to OpenGateRAG.

Copies `organization`, `user` (RAG quota/permission fields), `collection`, and
`document` rows. Chunks and embeddings live in Elasticsearch and are not copied.

The script is idempotent (`ON CONFLICT (id) DO NOTHING`), never deletes source
data, and can be dry-run with `DRY_RUN=true`.
"""

import asyncio
from datetime import datetime
import logging
import random
from typing import Any
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%y:%m:%d %H:%M:%S")
logger = logging.getLogger(__name__)

BATCH_SIZE = 500
SANITY_CHECK_SAMPLE = 100


# ============================== CONFIG ==============================


class Config(BaseSettings):
    source_postgres_url: str = Field(..., description="OpenGateLLM PostgreSQL URL (postgresql+asyncpg://...).")
    destination_postgres_url: str = Field(..., description="OpenGateRAG PostgreSQL URL (postgresql+asyncpg://...).")
    dry_run: bool = Field(default=False, description="If true, inspect and log what would be copied without writing.")

    @field_validator("source_postgres_url", "destination_postgres_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("PostgreSQL URL must use postgresql:// or postgresql+asyncpg://")
        return value


# ============================== DATABASE ==============================


class PostgreSQL:
    def __init__(self, url: str, label: str):
        self.url = url
        self.label = label
        self.engine: AsyncEngine = create_async_engine(url, echo=False, pool_size=5, max_overflow=0, pool_pre_ping=True)

    async def connect(self) -> AsyncConnection:
        return await self.engine.connect()

    async def dispose(self) -> None:
        await self.engine.dispose()


async def table_exists(connection: AsyncConnection, table: str) -> bool:
    result = await connection.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :table"),
        {"table": table},
    )
    return result.scalar_one_or_none() is not None


async def columns_of(connection: AsyncConnection, table: str) -> set[str]:
    result = await connection.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :table"),
        {"table": table},
    )
    return {row[0] for row in result.fetchall()}


async def require_tables(connection: AsyncConnection, label: str, tables: list[str]) -> None:
    missing = [table for table in tables if not await table_exists(connection, table)]
    if missing:
        raise RuntimeError(f"{label} database is missing required tables: {', '.join(missing)}")


async def require_columns(connection: AsyncConnection, label: str, table: str, columns: list[str]) -> set[str]:
    existing = await columns_of(connection, table)
    missing = [column for column in columns if column not in existing]
    if missing:
        raise RuntimeError(f"{label} table '{table}' is missing required columns: {', '.join(missing)}")
    return existing


async def enum_labels(connection: AsyncConnection, type_name: str) -> list[str]:
    result = await connection.execute(
        text(
            """
            SELECT e.enumlabel
            FROM pg_enum e
            JOIN pg_type t ON t.oid = e.enumtypid
            WHERE t.typname = :type_name
            ORDER BY e.enumsortorder
            """
        ),
        {"type_name": type_name},
    )
    return [row[0] for row in result.fetchall()]


async def count_rows(connection: AsyncConnection, table: str) -> int:
    result = await connection.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
    return int(result.scalar_one())


def map_visibility(value: Any, destination_labels: list[str]) -> str:
    raw = getattr(value, "value", value)
    raw = str(raw)
    if not destination_labels:
        return raw
    by_upper = {label.upper(): label for label in destination_labels}
    if raw.upper() not in by_upper:
        raise RuntimeError(f"Unsupported collection visibility '{raw}'. Destination enum labels: {destination_labels}")
    return by_upper[raw.upper()]


def same_database(source_url: str, destination_url: str) -> bool:
    def key(url: str) -> tuple[str, str, str, str]:
        parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
        return (parsed.hostname or "", str(parsed.port or 5432), (parsed.path or "").lstrip("/"), parsed.username or "")

    return key(source_url) == key(destination_url)


def batched(rows: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [rows[i : i + size] for i in range(0, len(rows), size)]


# ============================== FETCH ==============================


async def fetch_organizations(source: AsyncConnection) -> list[dict[str, Any]]:
    result = await source.execute(text("SELECT id, name, created, updated FROM organization ORDER BY id"))
    return [dict(row._mapping) for row in result.fetchall()]


async def fetch_users(source: AsyncConnection, source_columns: dict[str, set[str]]) -> list[dict[str, Any]]:
    user_columns = source_columns["user"]
    role_columns = source_columns.get("role", set())
    has_permission = "permission" in source_columns and "permission" in source_columns.get("permission", set())

    storage_limit_sql = "r.storage_limit" if "storage_limit" in role_columns else "NULL"
    join_role = "LEFT JOIN role r ON r.id = u.role_id" if "role" in source_columns else ""
    created_sql = "u.created" if "created" in user_columns else "NOW()"
    updated_sql = "u.updated" if "updated" in user_columns else created_sql
    if has_permission:
        permission_sql = """
            EXISTS (
                SELECT 1
                FROM permission p
                WHERE p.role_id = u.role_id
                  AND UPPER(p.permission::text) = 'CREATE_PUBLIC_COLLECTION'
            )
        """
    else:
        permission_sql = "FALSE"

    result = await source.execute(
        text(
            f"""
            SELECT
                u.id,
                {created_sql} AS created,
                {updated_sql} AS updated,
                {storage_limit_sql} AS storage_limit,
                {permission_sql} AS create_public_collection
            FROM "user" u
            {join_role}
            ORDER BY u.id
            """
        )
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def fetch_collections(source: AsyncConnection) -> list[dict[str, Any]]:
    result = await source.execute(
        text(
            """
            SELECT id, user_id, name, description, visibility::text AS visibility, created, updated
            FROM collection
            ORDER BY id
            """
        )
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def fetch_documents(source: AsyncConnection, document_columns: set[str]) -> list[dict[str, Any]]:
    size_sql = "size" if "size" in document_columns else "0"
    result = await source.execute(
        text(
            f"""
            SELECT id, collection_id, name, {size_sql} AS size, created
            FROM document
            ORDER BY id
            """
        )
    )
    return [dict(row._mapping) for row in result.fetchall()]


# ============================== INSERT ==============================


async def insert_rows(destination: AsyncConnection, statement: str, rows: list[dict[str, Any]], entity: str) -> int:
    if not rows:
        logger.info(f"No {entity} rows to insert.")
        return 0

    inserted = 0
    for batch in batched(rows, BATCH_SIZE):
        result = await destination.execute(text(statement), batch)
        inserted += result.rowcount if result.rowcount is not None and result.rowcount >= 0 else len(batch)
    logger.info(f"Copied {len(rows)} {entity} row(s) (conflict rows are skipped).")
    return inserted


async def reset_sequence(destination: AsyncConnection, table: str, column: str = "id") -> None:
    qualified = f'"{table}"'
    result = await destination.execute(text(f"SELECT pg_get_serial_sequence('{qualified}', '{column}')"))
    sequence = result.scalar_one_or_none()
    if not sequence:
        fallback = f"{table}_{column}_seq"
        exists = await destination.execute(text("SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = :name"), {"name": fallback})
        if exists.scalar_one_or_none() is None:
            logger.warning(f"No serial/identity sequence found for {table}.{column}; skipped reset.")
            return
        sequence = fallback
    await destination.execute(
        text(f"SELECT setval(:sequence, (SELECT COALESCE(MAX({column}), 1) FROM {qualified}), true)"),
        {"sequence": sequence},
    )
    logger.info(f"Reset sequence {sequence} from MAX({table}.{column}).")


# ============================== MIGRATION ==============================


async def migrate(config: Config, source: AsyncConnection, destination: AsyncConnection) -> None:
    await require_tables(source, "Source (OpenGateLLM)", ["user", "collection", "document"])
    await require_tables(destination, "Destination (OpenGateRAG)", ["user", "collection", "document"])

    await require_columns(source, "Source", "collection", ["id", "user_id", "name", "description", "visibility", "created", "updated"])
    source_document_columns = await require_columns(source, "Source", "document", ["id", "collection_id", "name", "created"])
    await require_columns(destination, "Destination", "user", ["id", "create_public_collection", "storage_limit", "created", "updated"])
    await require_columns(destination, "Destination", "collection", ["id", "user_id", "name", "description", "visibility", "created", "updated"])
    await require_columns(destination, "Destination", "document", ["id", "collection_id", "name", "size", "created"])

    source_columns = {
        "user": await columns_of(source, "user"),
        "collection": await columns_of(source, "collection"),
        "document": source_document_columns,
    }
    if await table_exists(source, "role"):
        source_columns["role"] = await columns_of(source, "role")
    if await table_exists(source, "permission"):
        source_columns["permission"] = await columns_of(source, "permission")

    copy_organizations = await table_exists(source, "organization") and await table_exists(destination, "organization")
    if copy_organizations:
        await require_columns(source, "Source", "organization", ["id", "name", "created", "updated"])
        await require_columns(destination, "Destination", "organization", ["id", "name", "created", "updated"])

    destination_visibility = await enum_labels(destination, "collectionvisibility")
    logger.info(f"Destination collectionvisibility labels: {destination_visibility or '(none / not an enum)'}")

    organizations = await fetch_organizations(source) if copy_organizations else []
    users = await fetch_users(source, source_columns)
    collections = await fetch_collections(source)
    documents = await fetch_documents(source, source_document_columns)

    public_collection_users = sum(1 for user in users if user["create_public_collection"])
    users_with_storage_limit = sum(1 for user in users if user["storage_limit"] is not None)

    logger.info(f"Source organizations: {len(organizations)}" + ("" if copy_organizations else " (skipped: table missing)"))
    logger.info(
        f"Source users: {len(users)} ({public_collection_users} with create_public_collection, {users_with_storage_limit} with storage_limit)"
    )
    logger.info(f"Source collections: {len(collections)}")
    logger.info(f"Source documents: {len(documents)}")
    logger.info(
        "Destination already has "
        f"{await count_rows(destination, 'user')} users, "
        f"{await count_rows(destination, 'collection')} collections, "
        f"{await count_rows(destination, 'document')} documents"
    )

    collection_user_ids = {collection["user_id"] for collection in collections}
    user_ids = {user["id"] for user in users}
    missing_owners = sorted(collection_user_ids - user_ids)
    if missing_owners:
        raise RuntimeError(f"Collections reference user ids missing from source user table: {missing_owners[:20]}")

    collection_ids = {collection["id"] for collection in collections}
    orphan_documents = [document["id"] for document in documents if document["collection_id"] not in collection_ids]
    if orphan_documents:
        raise RuntimeError(f"Documents reference collection ids missing from source collection table: {orphan_documents[:20]}")

    for collection in collections:
        collection["visibility"] = map_visibility(collection["visibility"], destination_visibility)

    if config.dry_run:
        logger.info("DRY_RUN=true: no rows will be written to the destination database.")
        return

    if copy_organizations:
        await insert_rows(
            destination,
            """
            INSERT INTO organization (id, name, created, updated)
            VALUES (:id, :name, :created, :updated)
            ON CONFLICT (id) DO NOTHING
            """,
            organizations,
            "organization",
        )

    await insert_rows(
        destination,
        """
        INSERT INTO "user" (id, create_public_collection, storage_limit, created, updated)
        VALUES (:id, :create_public_collection, :storage_limit, :created, :updated)
        ON CONFLICT (id) DO NOTHING
        """,
        users,
        "user",
    )
    await insert_rows(
        destination,
        """
        INSERT INTO collection (id, user_id, name, description, visibility, created, updated)
        VALUES (:id, :user_id, :name, :description, CAST(:visibility AS collectionvisibility), :created, :updated)
        ON CONFLICT (id) DO NOTHING
        """,
        collections,
        "collection",
    )
    await insert_rows(
        destination,
        """
        INSERT INTO document (id, collection_id, name, size, created)
        VALUES (:id, :collection_id, :name, :size, :created)
        ON CONFLICT (id) DO NOTHING
        """,
        documents,
        "document",
    )

    if copy_organizations:
        await reset_sequence(destination, "organization")
    await reset_sequence(destination, "user")
    await reset_sequence(destination, "collection")
    await reset_sequence(destination, "document")


async def sanity_check(source: AsyncConnection, destination: AsyncConnection) -> None:
    pairs = [("user", "id"), ("collection", "id"), ("document", "id")]
    if await table_exists(source, "organization") and await table_exists(destination, "organization"):
        pairs.insert(0, ("organization", "id"))

    for table, _column in pairs:
        source_count = await count_rows(source, table)
        destination_count = await count_rows(destination, table)
        logger.info(f"Count {table}: source={source_count} destination={destination_count}")
        if destination_count < source_count:
            logger.error(f"Destination {table} has fewer rows than source ({destination_count} < {source_count})")

    source_collections = await fetch_collections(source)
    if not source_collections:
        logger.info("No collections to spot-check.")
        return

    sample = random.sample(source_collections, k=min(SANITY_CHECK_SAMPLE, len(source_collections)))
    destination_visibility = await enum_labels(destination, "collectionvisibility")
    mismatches = 0
    for collection in sample:
        result = await destination.execute(
            text(
                """
                SELECT id, user_id, name, description, visibility::text AS visibility
                FROM collection
                WHERE id = :id
                """
            ),
            {"id": collection["id"]},
        )
        row = result.mappings().one_or_none()
        if row is None:
            logger.error(f"Collection {collection['id']} is missing from destination")
            mismatches += 1
            continue
        expected_visibility = map_visibility(collection["visibility"], destination_visibility)
        if row["user_id"] != collection["user_id"] or row["name"] != collection["name"] or row["visibility"] != expected_visibility:
            logger.error(f"Collection {collection['id']} differs between source and destination")
            mismatches += 1

    source_documents = await fetch_documents(source, await columns_of(source, "document"))
    if source_documents:
        document_sample = random.sample(source_documents, k=min(SANITY_CHECK_SAMPLE, len(source_documents)))
        for document in document_sample:
            result = await destination.execute(
                text("SELECT id, collection_id, name, size FROM document WHERE id = :id"),
                {"id": document["id"]},
            )
            row = result.mappings().one_or_none()
            if row is None:
                logger.error(f"Document {document['id']} is missing from destination")
                mismatches += 1
                continue
            if row["collection_id"] != document["collection_id"] or row["name"] != document["name"] or row["size"] != document["size"]:
                logger.error(f"Document {document['id']} differs between source and destination")
                mismatches += 1

    if mismatches:
        logger.error(f"Sanity check found {mismatches} mismatch(es).")
    else:
        logger.info("Sanity check passed for sampled collections and documents.")


async def main() -> None:
    logger.info(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    config = Config()

    if same_database(config.source_postgres_url, config.destination_postgres_url):
        raise RuntimeError("SOURCE_POSTGRES_URL and DESTINATION_POSTGRES_URL must point to different databases.")

    source = PostgreSQL(config.source_postgres_url, "source")
    destination = PostgreSQL(config.destination_postgres_url, "destination")
    source_connection = await source.connect()
    destination_connection = await destination.connect()

    try:
        if config.dry_run:
            await migrate(config=config, source=source_connection, destination=destination_connection)
            logger.info("Dry-run completed. Re-run with DRY_RUN=false to copy data.")
            return

        async with destination_connection.begin():
            await migrate(config=config, source=source_connection, destination=destination_connection)
        logger.info("Migration successfully completed!")
        await sanity_check(source=source_connection, destination=destination_connection)
        logger.info("Elasticsearch chunks/embeddings were not copied. Keep OGR pointed at the existing index.")
    except Exception as error:
        logger.exception(f"Migration failed: {error}")
        raise
    finally:
        await source_connection.close()
        await destination_connection.close()
        await source.dispose()
        await destination.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nMigration interrupted by user (Ctrl+C). Exiting...")
