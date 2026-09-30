"""Compare one user's usage between PostgreSQL and Langfuse, to validate the Postgre->Langfuse usage migration in dev.

Three comparisons:
1. the daily buckets over the window: requests, prompt / completion / total tokens, cost, kWh, kgCO2eq
2. the totals over the window
3. the per-endpoint, per-model and per-key totals

Usage :

    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-compare.py --user-id 42
    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-compare.py --user-id 42 --days 7 --retries 4
"""

import argparse
import asyncio
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import BackgroundTasks  # noqa: E402
from langfuse import Langfuse  # noqa: E402
from pydantic import AliasChoices, Field, field_validator  # noqa: E402
from pydantic_settings import BaseSettings, SettingsConfigDict  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import URL, make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from api.domain.usage.entities import UsageBucket  # noqa: E402
from api.infrastructure.langfuse import LangfuseUsageRepository  # noqa: E402
from api.infrastructure.postgres import PostgresUsageRepository  # noqa: E402

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s", datefmt="%y:%m:%d %H:%M:%S", force=True)
logger = logging.getLogger(__name__)

MAX_BUCKETS = 400
TOP_FILTER_VALUES = 5
METRICS: list[tuple[str, Callable[[UsageBucket], float], bool]] = [
    ("requests", lambda bucket: bucket.requests, True),
    ("prompt_tokens", lambda bucket: bucket.prompt_tokens, True),
    ("completion_tokens", lambda bucket: bucket.completion_tokens, True),
    ("total_tokens", lambda bucket: bucket.total_tokens, True),
    ("cost", lambda bucket: bucket.cost, False),
    ("kWh", lambda bucket: bucket.impacts.kWh, False),
    ("kgCO2eq", lambda bucket: bucket.impacts.kgCO2eq, False),
]
METRIC_BY_NAME = {name: (read, integer) for name, read, integer in METRICS}
TOKEN_METRICS = ("prompt_tokens", "completion_tokens", "total_tokens")
SCORE_METRICS = ("cost", "kWh", "kgCO2eq")


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = Field(..., description="OpenGateLLM PostgreSQL URL (postgresql+asyncpg://...), credentials optional.")
    postgres_user: str = Field(default="", description="Injected into POSTGRES_URL when it carries no user.")
    postgres_password: str = Field(default="", description="Injected into POSTGRES_URL when it carries no password.")
    langfuse_public_key: str = Field(..., description="Langfuse project public key (pk-lf-...).")
    langfuse_secret_key: str = Field(..., description="Langfuse project secret key (sk-lf-...).")
    langfuse_base_url: str = Field(
        ..., validation_alias=AliasChoices("langfuse_base_url", "langfuse_host"), description="Langfuse base URL (LANGFUSE_HOST is accepted too)."
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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-id", type=int, required=True, help="User id whose usage is compared.")
    parser.add_argument("--days", type=int, default=30, help="Window size in days, ending now (default 30). Ignored when --start is given.")
    parser.add_argument("--start", type=_parse_day, default=None, help="Window start, UTC ISO 8601.")
    parser.add_argument("--end", type=_parse_day, default=None, help="Window end, UTC ISO 8601 (default: now).")
    parser.add_argument("--tolerance", type=float, default=1e-6, help="Relative tolerance on the float metrics (cost, impacts).")
    parser.add_argument("--retries", type=int, default=0, help="Re-compare that many times while it does not match, for ingestion lag.")
    parser.add_argument("--retry-delay", type=float, default=20.0, help="Seconds between two attempts (default 20).")
    parser.add_argument("--no-filters", action="store_true", help="Skip the per-endpoint / per-model / per-key comparisons.")
    return parser.parse_args()


def _parse_day(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def window_of(arguments: argparse.Namespace) -> tuple[datetime, datetime]:
    end_time = arguments.end or datetime.now(tz=UTC)
    start_time = arguments.start or (end_time - timedelta(days=arguments.days))
    if start_time >= end_time:
        raise ValueError("--start must be strictly before --end")
    return start_time, end_time


def matches(left: float, right: float, integer: bool, tolerance: float) -> bool:
    if integer:
        return int(left) == int(right)
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def format_value(value: float, integer: bool) -> str:
    return f"{int(value)}" if integer else f"{value:.6f}"


def empty_bucket() -> UsageBucket:
    """A missing bucket reads as zeros, so a day present on one side only still compares."""
    now = datetime.now(tz=UTC)
    return UsageBucket(start_time=now, end_time=now)


def paired_columns(
    postgres: UsageBucket | None,
    langfuse: UsageBucket | None,
    names: tuple[str, ...],
    tolerance: float,
) -> tuple[list[str], bool]:
    """One `postgres` then one `langfuse` cell per metric, plus whether they all match."""
    left, right = postgres or empty_bucket(), langfuse or empty_bucket()
    cells, matching = [], True
    for name in names:
        read, integer = METRIC_BY_NAME[name]
        postgres_value, langfuse_value = read(left), read(right)
        cells += [format_value(postgres_value, integer), format_value(langfuse_value, integer)]
        matching = matching and matches(postgres_value, langfuse_value, integer, tolerance)
    return cells, matching


def presence_of(postgres: UsageBucket | None, langfuse: UsageBucket | None) -> str:
    if postgres is None:
        return "langfuse only"
    return "postgres only" if langfuse is None else "both"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    """Aligned plain-text table: header, rule, rows. First column left-aligned, the others right-aligned."""
    widths = [max([len(header), *(len(row[index]) for row in rows)]) for index, header in enumerate(headers)]

    def line(cells: list[str]) -> str:
        padded = (cell.ljust(width) if index == 0 else cell.rjust(width) for index, (cell, width) in enumerate(zip(cells, widths)))
        return "  ".join(padded).rstrip()

    return "\n".join([line(headers), "  ".join("-" * width for width in widths), *(line(row) for row in rows)])


def totals_of(buckets: list[UsageBucket]) -> UsageBucket:
    return UsageBucket(
        start_time=datetime.now(tz=UTC),
        end_time=datetime.now(tz=UTC),
        prompt_tokens=sum(bucket.prompt_tokens for bucket in buckets),
        completion_tokens=sum(bucket.completion_tokens for bucket in buckets),
        total_tokens=sum(bucket.total_tokens for bucket in buckets),
        cost=sum(bucket.cost for bucket in buckets),
        requests=sum(bucket.requests for bucket in buckets),
        impacts={"kWh": sum(bucket.impacts.kWh for bucket in buckets), "kgCO2eq": sum(bucket.impacts.kgCO2eq for bucket in buckets)},
    )


def by_day(buckets: list[UsageBucket]) -> dict[date, UsageBucket]:
    return {bucket.start_time.astimezone(UTC).date(): bucket for bucket in buckets}


async def read_both(
    postgres_repository: PostgresUsageRepository,
    langfuse_repository: LangfuseUsageRepository,
    *,
    user_id: int,
    start_time: datetime,
    end_time: datetime,
    endpoint: str | None = None,
    model: str | None = None,
    key_id: int | None = None,
) -> tuple[list[UsageBucket], list[UsageBucket]]:
    arguments = {
        "user_id": user_id,
        "start_time": start_time,
        "end_time": end_time,
        "offset": 0,
        "limit": MAX_BUCKETS,
        "endpoint": endpoint,
        "model": model,
        "key_id": key_id,
    }
    postgres_page, langfuse_page = await asyncio.gather(
        postgres_repository.get_usage_buckets_page(**arguments),
        langfuse_repository.get_usage_buckets_page(**arguments),
    )
    return list(postgres_page.data), list(langfuse_page.data)


async def top_values(session: AsyncSession, column: str, user_id: int, start_time: datetime, end_time: datetime) -> list[tuple[str, int]]:
    """Most used endpoints / router names / key ids of that user, read from Postgres."""
    query = text(
        f"SELECT {column} AS value, count(*) AS requests FROM usage "  # noqa: S608 - column is a literal from the caller
        "WHERE user_id = :user_id AND status >= 200 AND status < 300 AND created >= :start_time AND created <= :end_time "
        f"AND {column} IS NOT NULL GROUP BY {column} ORDER BY requests DESC LIMIT :limit"
    )
    parameters = {"user_id": user_id, "start_time": start_time, "end_time": end_time, "limit": TOP_FILTER_VALUES}
    result = await session.execute(query, parameters)
    return [(row.value, row.requests) for row in result.all()]


async def compare(
    session: AsyncSession,
    postgres_repository: PostgresUsageRepository,
    langfuse_repository: LangfuseUsageRepository,
    arguments: argparse.Namespace,
    start_time: datetime,
    end_time: datetime,
) -> bool:
    postgres_buckets, langfuse_buckets = await read_both(
        postgres_repository, langfuse_repository, user_id=arguments.user_id, start_time=start_time, end_time=end_time
    )
    postgres_days, langfuse_days = by_day(postgres_buckets), by_day(langfuse_buckets)
    if not postgres_days and not langfuse_days:
        logger.warning(f"No usage at all for user {arguments.user_id} between {start_time.isoformat()} and {end_time.isoformat()}.")
        return True

    days = sorted(set(postgres_days) | set(langfuse_days))
    matching = True

    # Fine-grained first: what the backfill has to carry over verbatim, token by token and score by score.
    token_rows, score_rows = [], []
    for day in days:
        postgres_bucket, langfuse_bucket = postgres_days.get(day), langfuse_days.get(day)
        presence = presence_of(postgres_bucket, langfuse_bucket)
        for metrics, rows in ((TOKEN_METRICS, token_rows), (SCORE_METRICS, score_rows)):
            cells, day_matching = paired_columns(postgres_bucket, langfuse_bucket, metrics, arguments.tolerance)
            rows.append([str(day), *cells, presence, "ok" if day_matching else "MISMATCH"])
            matching = matching and day_matching

    logger.info(
        "TOKENS PER DAY\n"
        + render_table(
            ["day", "prompt pg", "prompt lf", "completion pg", "completion lf", "total pg", "total lf", "presence", "status"],
            token_rows,
        )
    )
    logger.info(
        "COST AND IMPACT SCORES PER DAY\n"
        + render_table(
            ["day", "cost pg", "cost lf", "kWh pg", "kWh lf", "kgCO2eq pg", "kgCO2eq lf", "presence", "status"],
            score_rows,
        )
    )

    postgres_totals, langfuse_totals = totals_of(postgres_buckets), totals_of(langfuse_buckets)
    if not arguments.no_filters:
        matching = await report_filters(
            session,
            postgres_repository,
            langfuse_repository,
            arguments,
            start_time,
            end_time,
            matching=matching,
            langfuse_requests=langfuse_totals.requests,
        )

    request_rows = []
    for day in days:
        postgres_bucket, langfuse_bucket = postgres_days.get(day), langfuse_days.get(day)
        left = postgres_bucket.requests if postgres_bucket else 0
        right = langfuse_bucket.requests if langfuse_bucket else 0
        request_rows.append([str(day), str(left), str(right), f"{right - left:+}", "ok" if left == right else "MISMATCH"])
    left, right = postgres_totals.requests, langfuse_totals.requests
    request_rows.append(["TOTAL", str(left), str(right), f"{right - left:+}", "ok" if left == right else "MISMATCH"])
    logger.info("REQUESTS PER DAY\n" + render_table(["day", "postgres", "langfuse", "delta", "status"], request_rows))

    summary_rows = [["days covered", str(len(postgres_days)), str(len(langfuse_days)), "", "ok" if len(postgres_days) == len(langfuse_days) else "MISMATCH"]]  # fmt: off
    for name, read, integer in METRICS:
        left, right = read(postgres_totals), read(langfuse_totals)
        delta = f"{right - left:+}" if integer else f"{right - left:+.6f}"
        status = "ok" if matches(left, right, integer, arguments.tolerance) else "MISMATCH"
        summary_rows.append([name, format_value(left, integer), format_value(right, integer), delta, status])
    logger.info("SUMMARY OVER THE WINDOW\n" + render_table(["metric", "postgres", "langfuse", "delta", "status"], summary_rows))

    return matching


async def report_filters(
    session: AsyncSession,
    postgres_repository: PostgresUsageRepository,
    langfuse_repository: LangfuseUsageRepository,
    arguments: argparse.Namespace,
    start_time: datetime,
    end_time: datetime,
    *,
    matching: bool,
    langfuse_requests: int,
) -> bool:
    """Per-endpoint / per-model / per-key totals: the filters a bucket total can match while they return nothing."""
    rows = []
    empty_endpoint_filters = 0
    endpoint_filters = 0
    for label, column, keyword, cast in (
        ("endpoint", "endpoint", "endpoint", str),
        ("model", "router_name", "model", str),
        ("key", "token_id", "key_id", int),
    ):
        for value, _ in await top_values(session, column, arguments.user_id, start_time, end_time):
            filtered_postgres, filtered_langfuse = await read_both(
                postgres_repository,
                langfuse_repository,
                user_id=arguments.user_id,
                start_time=start_time,
                end_time=end_time,
                **{keyword: cast(value)},
            )
            left, right = totals_of(filtered_postgres), totals_of(filtered_langfuse)
            cells, filter_matching = paired_columns(left, right, ("total_tokens",), arguments.tolerance)
            filter_matching = filter_matching and left.requests == right.requests
            if label == "endpoint":
                endpoint_filters += 1
                empty_endpoint_filters += 1 if right.requests == 0 and left.requests > 0 else 0
            matching = matching and filter_matching
            rows.append([label, str(value), str(left.requests), str(right.requests), *cells, "ok" if filter_matching else "MISMATCH"])

    logger.info(
        "FILTERS — trace name, providedModelName, key_id tag\n"
        + render_table(["filter", "value", "requests pg", "requests lf", "tokens pg", "tokens lf", "status"], rows)
    )

    # Only a naming mismatch when Langfuse does hold requests over the window: an empty project trips every filter anyway.
    if endpoint_filters and empty_endpoint_filters == endpoint_filters and langfuse_requests > 0:
        logger.warning(
            "Every endpoint filter comes back empty on Langfuse while Postgres has rows: look at the read path, not the backfill. "
            "`LangfuseUsageRepository._context_filters` matches `traceName` exactly against the `EndpointUsage` value ('/v1/ocr', ...), "
            "so traces written under another name (the 'ocr' / 'chat-completions' form used before commit ae8b106f) never match."
        )

    return matching


async def main() -> None:
    arguments = parse_arguments()
    config = Config()
    start_time, end_time = window_of(arguments)

    client = Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key,
        base_url=config.langfuse_base_url,
        environment=config.langfuse_environment,
        tracing_enabled=False,
    )
    if not client.auth_check():
        raise RuntimeError(f"Langfuse authentication failed against {config.langfuse_base_url}")

    engine = create_async_engine(config.database_url(), echo=False, pool_size=5, max_overflow=0, pool_pre_ping=True)
    matching = False
    try:
        async with AsyncSession(engine) as session:
            postgres_repository = PostgresUsageRepository(postgres_session=session, background_tasks=BackgroundTasks())
            langfuse_repository = LangfuseUsageRepository(client=client)
            logger.info(f"Comparing user {arguments.user_id} from {start_time.isoformat()} to {end_time.isoformat()}")
            for attempt in range(arguments.retries + 1):
                matching = await compare(session, postgres_repository, langfuse_repository, arguments, start_time, end_time)
                if matching or attempt == arguments.retries:
                    break
                logger.info(f"Attempt {attempt + 1}/{arguments.retries + 1} did not match, retrying in {arguments.retry_delay}s (ingestion lag).")
                await asyncio.sleep(arguments.retry_delay)
    finally:
        client.shutdown()
        await engine.dispose()

    logger.info("RESULT: PASS" if matching else "RESULT: MISMATCH")
    raise SystemExit(0 if matching else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nComparison interrupted by user (Ctrl+C). Exiting...")
