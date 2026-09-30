"""Backfill the PostgreSQL `usage` table into Langfuse (v4), so `GET /v1/usage` keeps its history.

Usage

    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-backfill.py --dry-run --limit 20
    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-backfill.py --user-id 42 --limit 20
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
import hashlib
import logging
from typing import Any

from langfuse import Langfuse, propagate_attributes
from opentelemetry.sdk.trace.id_generator import IdGenerator
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%y:%m:%d %H:%M:%S", force=True)
logger = logging.getLogger(__name__)

BATCH_SIZE = 500
KWH_SCORE = "kWh"
KGCO2EQ_SCORE = "kgCO2eq"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
COLUMNS = (
    "id",
    "created",
    "user_id",
    "user_email",
    "token_id",
    "token_name",
    "router_id",
    "router_name",
    "provider_id",
    "provider_model_name",
    "request_id",
    "endpoint",
    "latency",
    "ttft",
    "status",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cost",
    "kwh",
    "kgco2eq",
)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = Field(..., description="OpenGateLLM PostgreSQL URL (postgresql+asyncpg://...), credentials optional.")
    postgres_user: str = Field(default="", description="Injected into POSTGRES_URL when it carries no user.")
    postgres_password: str = Field(default="", description="Injected into POSTGRES_URL when it carries no password.")
    langfuse_public_key: str = Field(default="", description="Langfuse project public key (pk-lf-...). Not needed with --dry-run.")
    langfuse_secret_key: str = Field(default="", description="Langfuse project secret key (sk-lf-...). Not needed with --dry-run.")
    langfuse_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("langfuse_base_url", "langfuse_host"),
        description="Langfuse base URL (LANGFUSE_HOST is accepted too). Not needed with --dry-run.",
    )
    langfuse_environment: str | None = Field(default=None, description="Langfuse environment, must match the one the API writes to.")

    @field_validator("postgres_url", mode="before")
    @classmethod
    def normalize_postgres_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("PostgreSQL URL must use postgresql:// or postgresql+asyncpg://")
        return value

    def database_url(self) -> URL:
        """Keep the credentials out of POSTGRES_URL: SQLAlchemy escapes them, no percent-encoding needed."""
        url = make_url(self.postgres_url)
        if self.postgres_user and not url.username:
            url = url.set(username=self.postgres_user)
        if self.postgres_password and not url.password:
            url = url.set(password=self.postgres_password)
        if not url.password:
            logger.warning("No password in POSTGRES_URL nor POSTGRES_PASSWORD: asyncpg will fall back to PGPASSWORD or ~/.pgpass.")
        return url

    def require_langfuse(self) -> None:
        missing = [name for name in ("langfuse_public_key", "langfuse_secret_key", "langfuse_base_url") if not getattr(self, name)]
        if missing:
            raise ValueError(f"Missing Langfuse credentials: {', '.join(name.upper() for name in missing)}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=_parse_day, default=None, help="Only replay rows created at or after this UTC date/datetime (ISO 8601).")
    parser.add_argument("--end", type=_parse_day, default=None, help="Only replay rows created strictly before this UTC date/datetime (ISO 8601).")
    parser.add_argument("--user-id", type=int, default=None, help="Only replay rows of that user id.")
    parser.add_argument("--after-id", type=int, default=0, help="Resume after that `usage.id` (the script logs the last id of every batch).")
    parser.add_argument("--limit", type=int, default=None, help="Stop after that many rows, for a first smoke test.")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help=f"Rows read, ingested and flushed per batch (default {BATCH_SIZE}).")
    parser.add_argument("--batch-pause", type=float, default=1, help="Seconds to wait between batches, to spare a small Langfuse instance.")
    parser.add_argument("--include-failed", action=argparse.BooleanOptionalAction, default=True, help="Replay non-2xx rows too, as ERROR generations without usage or cost (default: enabled, --no-include-failed to skip them).")  # fmt: off
    parser.add_argument("--skip-impacts", action="store_true", help="Do not replay the kWh / kgCO2eq scores.")
    parser.add_argument("--dry-run", action="store_true", help="Read and log what would be sent, without touching Langfuse.")
    return parser.parse_args()


def _parse_day(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


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


def _is_langfuse_trace_id(value: str) -> bool:
    return len(value) == 32 and all(character in "0123456789abcdef" for character in value) and int(value, 16) != 0


def trace_id_of(row: dict[str, Any]) -> str:
    """Reuse `request_id` as the trace id: it is a `uuid4().hex`, which is exactly a Langfuse trace id."""
    request_id = (row["request_id"] or "").lower()
    return request_id if _is_langfuse_trace_id(request_id) else _digest("usage-trace", row["id"], length=32)


def span_id_of(trace_id: str) -> str:
    return _digest("usage-span", trace_id, length=16)


def score_id_of(trace_id: str, name: str) -> str:
    return _digest("usage-score", trace_id, name, length=32)


def to_nanos(value: datetime) -> int:
    """Integer arithmetic only: `datetime.timestamp()` is a float and loses nanoseconds."""
    delta = value.astimezone(UTC) - EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1_000


class PostgreSQL:
    def __init__(self, url: URL):
        self.engine: AsyncEngine = create_async_engine(url, echo=False, pool_size=5, max_overflow=0, pool_pre_ping=True)

    async def connect(self) -> AsyncConnection:
        return await self.engine.connect()

    async def dispose(self) -> None:
        await self.engine.dispose()


async def require_usage_table(connection: AsyncConnection) -> None:
    result = await connection.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'usage'")
    )
    columns = {row[0] for row in result.fetchall()}
    if not columns:
        raise RuntimeError("Table `usage` not found in the source database")
    missing = sorted(set(COLUMNS) - columns)
    if missing:
        raise RuntimeError(f"Table `usage` is missing the expected columns: {', '.join(missing)}")


async def read_batch(connection: AsyncConnection, arguments: argparse.Namespace, after_id: int, size: int) -> list[dict[str, Any]]:
    conditions = ["id > :after_id"]
    parameters: dict[str, Any] = {"after_id": after_id, "size": size}
    if arguments.start is not None:
        conditions.append("created >= :start_time")
        parameters["start_time"] = arguments.start
    if arguments.end is not None:
        conditions.append("created < :end_time")
        parameters["end_time"] = arguments.end
    if arguments.user_id is not None:
        conditions.append("user_id = :user_id")
        parameters["user_id"] = arguments.user_id

    query = f"SELECT {', '.join(COLUMNS)} FROM usage WHERE {' AND '.join(conditions)} ORDER BY id LIMIT :size"
    result = await connection.execute(text(query), parameters)
    return [dict(row) for row in result.mappings().all()]


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
    details = {
        "input": row["prompt_tokens"],
        "output": row["completion_tokens"],
        "total": row["total_tokens"],
    }
    present = {key: int(value) for key, value in details.items() if value is not None}
    return present or None


def emit_generation(client: Langfuse, generator: PinnedIdGenerator, row: dict[str, Any]) -> tuple[str, str]:
    created = created_at(row)
    trace_id = trace_id_of(row)
    span_id = span_id_of(trace_id)
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
                "OpenTelemetry ignored the pinned id generator "
                f"(expected {trace_id}/{span_id}, got {generation.trace_id}/{generation.id}). "
                "A globally registered TracerProvider takes precedence; without pinned ids a re-run would duplicate every row."
            )
        generation.end(end_time=to_nanos(created + timedelta(milliseconds=row["latency"] or 0)))

    return trace_id, span_id


def emit_impacts(client: Langfuse, row: dict[str, Any], trace_id: str, span_id: str) -> int:
    created = created_at(row)
    emitted = 0
    for name, value in ((KWH_SCORE, row["kwh"]), (KGCO2EQ_SCORE, row["kgco2eq"])):
        if value is None:
            continue
        client.create_score(
            name=name,
            value=float(value),
            data_type="NUMERIC",
            trace_id=trace_id,
            observation_id=span_id,
            score_id=score_id_of(trace_id, name),
            timestamp=created,
        )
        emitted += 1
    return emitted


async def backfill(connection: AsyncConnection, client: Langfuse | None, generator: PinnedIdGenerator, arguments: argparse.Namespace) -> None:
    after_id = arguments.after_id
    read = generations = scores = skipped_no_user = skipped_failed = 0

    while True:
        size = arguments.batch_size if arguments.limit is None else min(arguments.batch_size, arguments.limit - read)
        if size <= 0:
            break

        rows = await read_batch(connection, arguments, after_id=after_id, size=size)
        if not rows:
            break

        read += len(rows)
        after_id = rows[-1]["id"]
        replayed: list[tuple[dict[str, Any], str, str]] = []

        for row in rows:
            if row["user_id"] is None:
                skipped_no_user += 1
                continue
            if not succeeded(row) and not arguments.include_failed:
                skipped_failed += 1
                continue
            if client is None:
                trace_id = trace_id_of(row)
                logger.info(
                    "[dry-run] %s %s user=%s model=%s trace=%s tokens=%s cost=%s impacts=(%s, %s)",
                    created_at(row).isoformat(),
                    row["endpoint"],
                    row["user_id"],
                    row["router_name"],
                    trace_id,
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
            if not arguments.skip_impacts:
                for row, trace_id, span_id in replayed:
                    if succeeded(row):
                        scores += emit_impacts(client, row, trace_id, span_id)
                client.flush()

        logger.info(f"Replayed {generations} generations and {scores} scores over {read} rows (last usage.id = {after_id}).")

        if len(rows) < size:
            break
        if arguments.batch_pause > 0:
            await asyncio.sleep(arguments.batch_pause)

    logger.info(
        f"Done: {read} rows read, {generations} generations, {scores} scores, {skipped_no_user} skipped (no user), {skipped_failed} skipped (failed)."
    )
    if skipped_failed and not arguments.include_failed:
        logger.info("Failed rows are excluded from GET /v1/usage anyway. Re-run with --include-failed to see them in the Langfuse UI.")


async def main() -> None:
    arguments = parse_arguments()
    config = Config()
    if arguments.start is not None and arguments.end is not None and arguments.start >= arguments.end:
        raise ValueError("--start must be strictly before --end")

    client: Langfuse | None = None
    generator = PinnedIdGenerator()
    if not arguments.dry_run:
        config.require_langfuse()
        client = Langfuse(
            public_key=config.langfuse_public_key,
            secret_key=config.langfuse_secret_key,
            base_url=config.langfuse_base_url,
            environment=config.langfuse_environment,
            id_generator=generator,
        )
        if not client.auth_check():
            raise RuntimeError(f"Langfuse authentication failed against {config.langfuse_base_url}")

    postgres = PostgreSQL(config.database_url())
    connection = await postgres.connect()
    try:
        await require_usage_table(connection)
        await backfill(connection, client, generator, arguments)
        if arguments.dry_run:
            logger.info("Dry-run completed. Re-run without --dry-run to ingest into Langfuse.")
    except Exception as error:
        logger.exception(f"Backfill failed: {error}")
        raise
    finally:
        if client is not None:
            client.flush()
            client.shutdown()
        await connection.close()
        await postgres.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nBackfill interrupted by user (Ctrl+C). Exiting...")
