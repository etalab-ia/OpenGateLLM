"""Backfill the PostgreSQL `usage` table into Langfuse (v4), so `GET /v1/usage` keeps its history.

Usage

    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-backfill.py
    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-backfill.py
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import logging
from typing import Any

from langfuse import Langfuse, propagate_attributes
from opentelemetry.sdk.trace.id_generator import IdGenerator
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%y:%m:%d %H:%M:%S", force=True)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = Field(..., description="OpenGateLLM PostgreSQL URL (postgresql+asyncpg://...), credentials optional.")
    postgres_user: str = Field(default="", description="Injected into POSTGRES_URL when it carries no user.")
    postgres_password: str = Field(default="", description="Injected into POSTGRES_URL when it carries no password.")
    langfuse_public_key: str = Field(default="", description="Langfuse project public key (pk-lf-...). Not needed with --dry-run.")
    langfuse_secret_key: str = Field(default="", description="Langfuse project secret key (sk-lf-...). Not needed with --dry-run.")
    langfuse_base_url: str = Field(default="", validation_alias=AliasChoices("langfuse_base_url", "langfuse_host"))
    langfuse_environment: str | None = Field(default=None, description="Langfuse environment, must match the one the API writes to.")

    def database_url(self) -> URL:
        """Keep the credentials out of POSTGRES_URL: SQLAlchemy escapes them, no percent-encoding needed."""
        url = make_url(self.postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1))
        if self.postgres_user and not url.username:
            url = url.set(username=self.postgres_user)
        if self.postgres_password and not url.password:
            url = url.set(password=self.postgres_password)
        return url


class PinnedIdGenerator(IdGenerator):
    """Pins the ids of the next span, so that replaying a row overwrites its observation."""

    def __init__(self) -> None:
        self.trace_id = 0
        self.span_id = 0

    def generate_span_id(self) -> int:
        return self.span_id

    def generate_trace_id(self) -> int:
        return self.trace_id


def _digest(*parts: object, length: int) -> str:
    return hashlib.sha256(":".join(str(part) for part in parts).encode()).hexdigest()[:length]


def trace_id_of(row: dict[str, Any]) -> str:
    """Reuse `request_id` as the trace id: it is a `uuid4().hex`, which is exactly a Langfuse trace id."""
    request_id = (row["request_id"] or "").lower()
    usable = len(request_id) == 32 and all(character in "0123456789abcdef" for character in request_id) and int(request_id or "0", 16) != 0
    return request_id if usable else _digest("usage-trace", row["id"], length=32)


def to_nanos(value: datetime) -> int:
    """Integer arithmetic only: `datetime.timestamp()` is a float and loses nanoseconds."""
    delta = value.astimezone(UTC) - EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000


def succeeded(row: dict[str, Any]) -> bool:
    return row["status"] is not None and 200 <= row["status"] < 300


def created_at(row: dict[str, Any]) -> datetime:
    created = row["created"]
    return created.replace(tzinfo=UTC) if created.tzinfo is None else created.astimezone(UTC)


def metadata_of(row: dict[str, Any]) -> dict[str, Any]:
    """Same keys as `LangfuseUsageRepository.start_record`, so both sources are queried identically."""
    return {
        "router_id": row["router_id"],
        "router_name": row["router_name"],
        "user_email": row["user_email"],
        "key_id": str(row["token_id"]) if row["token_id"] is not None else None,
        "key_name": row["token_name"],
        "provider_id": row["provider_id"],
        "provider_model_name": row["provider_model_name"],
    }


def usage_details_of(row: dict[str, Any]) -> dict[str, int] | None:
    """`total` is sent explicitly: Langfuse only sums the other keys when it is absent."""
    details = {"input": row["prompt_tokens"], "output": row["completion_tokens"], "total": row["total_tokens"]}
    present = {key: int(value) for key, value in details.items() if value is not None}
    return present or None


async def read_batch(connection: AsyncConnection, user_id: int | None, after_id: int, size: int) -> list[dict[str, Any]]:
    conditions = ["id > :after_id"]
    parameters: dict[str, Any] = {"after_id": after_id, "size": size}
    if user_id is not None:
        conditions.append("user_id = :user_id")
        parameters["user_id"] = user_id

    query = f"SELECT * FROM usage WHERE {' AND '.join(conditions)} ORDER BY id LIMIT :size"
    result = await connection.execute(text(query), parameters)
    return [dict(row) for row in result.mappings().all()]


def emit_generation(client: Langfuse, generator: PinnedIdGenerator, row: dict[str, Any]) -> tuple[str, str]:
    created = created_at(row)
    trace_id = trace_id_of(row)
    span_id = _digest("usage-span", trace_id, length=16)
    generator.trace_id = int(trace_id, 16)
    generator.span_id = int(span_id, 16)

    failed = not succeeded(row)
    ttft = row["ttft"]
    tags = [f"key_id:{row['token_id']}"] if row["token_id"] is not None else None

    with propagate_attributes(user_id=str(row["user_id"]), tags=tags, trace_name=row["endpoint"]):
        otel_span = client._otel_tracer.start_span(name=row["endpoint"], start_time=to_nanos(created))
        generation = client._create_observation_from_otel_span(
            otel_span=otel_span,
            as_type="generation",
            metadata=metadata_of(row),
            level="ERROR" if failed else None,
            status_message=f"HTTP {row['status']}" if failed else None,
            completion_start_time=created + timedelta(milliseconds=ttft) if ttft is not None else None,
            model=row["router_name"],
            usage_details=None if failed else usage_details_of(row),
            cost_details=None if failed or row["cost"] is None else {"total": float(row["cost"])},
        )
        # An unended span is never exported, so bailing out here leaves nothing behind.
        if generation.trace_id != trace_id or generation.id != span_id:
            raise RuntimeError(
                f"OpenTelemetry ignored the pinned id generator (expected {trace_id}/{span_id}, got {generation.trace_id}/{generation.id}). "
                "A globally registered TracerProvider takes precedence; without pinned ids a re-run would duplicate every row."
            )
        generation.end(end_time=to_nanos(created + timedelta(milliseconds=row["latency"] or 0)))

    return trace_id, span_id


def emit_impacts(client: Langfuse, row: dict[str, Any], trace_id: str, span_id: str) -> int:
    emitted = 0
    for name, value in (("kWh", row["kwh"]), ("kgCO2eq", row["kgco2eq"])):
        if value is None:
            continue
        client.create_score(
            name=name,
            value=float(value),
            data_type="NUMERIC",
            trace_id=trace_id,
            observation_id=span_id,
            score_id=_digest("usage-score", trace_id, name, length=32),
            timestamp=created_at(row),
        )
        emitted += 1
    return emitted


async def backfill(connection: AsyncConnection, client: Langfuse | None, generator: PinnedIdGenerator, arguments: argparse.Namespace) -> None:
    after_id = arguments.after_id
    read = generations = scores = skipped = 0

    while True:
        size = BATCH_SIZE if arguments.limit is None else min(BATCH_SIZE, arguments.limit - read)
        if size <= 0:
            break

        rows = await read_batch(connection, user_id=arguments.user_id, after_id=after_id, size=size)
        if not rows:
            break

        read += len(rows)
        after_id = rows[-1]["id"]
        replayed: list[tuple[dict[str, Any], str, str]] = []

        for row in rows:
            if row["user_id"] is None:
                skipped += 1
                continue
            if client is None:
                logger.info(
                    "[dry-run] %s %s user=%s model=%s trace=%s tokens=%s cost=%s impacts=(%s, %s)",
                    created_at(row).isoformat(),
                    row["endpoint"],
                    row["user_id"],
                    row["router_name"],
                    trace_id_of(row),
                    usage_details_of(row),
                    row["cost"],
                    row["kwh"],
                    row["kgco2eq"],
                )
                generations += 1
                continue
            trace_id, span_id = emit_generation(client, generator, row)
            generations += 1
            replayed.append((row, trace_id, span_id))

        if client is not None:
            # Flush the spans before enqueuing their scores, so an observation always exists first.
            client.flush()
            for row, trace_id, span_id in replayed:
                if succeeded(row):
                    scores += emit_impacts(client, row, trace_id, span_id)
            client.flush()

        logger.info(f"Replayed {generations} generations and {scores} scores over {read} rows (last usage.id = {after_id}).")

        if len(rows) < size:
            break

    logger.info(f"Done: {read} rows read, {generations} generations, {scores} scores, {skipped} skipped (no user).")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-id", type=int, default=None, help="Only replay rows of that user id.")
    parser.add_argument("--after-id", type=int, default=0, help="Resume after that `usage.id` (the script logs the last id of every batch).")
    parser.add_argument("--limit", type=int, default=None, help="Stop after that many rows, for a first smoke test.")
    parser.add_argument("--dry-run", action="store_true", help="Read and log what would be sent, without touching Langfuse.")
    return parser.parse_args()


async def main() -> None:
    arguments = parse_arguments()
    config = Config()

    client: Langfuse | None = None
    generator = PinnedIdGenerator()
    if not arguments.dry_run:
        client = Langfuse(
            public_key=config.langfuse_public_key,
            secret_key=config.langfuse_secret_key,
            base_url=config.langfuse_base_url,
            environment=config.langfuse_environment,
            id_generator=generator,
        )
        if not client.auth_check():
            raise RuntimeError(f"Langfuse authentication failed against {config.langfuse_base_url}")

    engine = create_async_engine(config.database_url(), pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await backfill(connection, client, generator, arguments)
        if arguments.dry_run:
            logger.info("Dry-run completed. Re-run without --dry-run to ingest into Langfuse.")
    finally:
        if client is not None:
            client.flush()
            client.shutdown()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nBackfill interrupted by user (Ctrl+C). Exiting...")
