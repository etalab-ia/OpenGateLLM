"""Compare one user's usage between PostgreSQL and Langfuse, to validate the Postgre->Langfuse usage migration in dev.

Three comparisons:
1. the daily buckets over the window: requests, prompt / completion / total tokens, cost, kWh, kgCO2eq
2. the totals over the window
3. the per-endpoint, per-model and per-key totals

Usage :

    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-compare.py --user-id 42
    ./env/bin/python adr/scripts/2026-09-30-langfuse-usage-compare.py --user-id 42 --days 7
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
from pydantic import AliasChoices, Field  # noqa: E402
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
METRICS: dict[str, tuple[Callable[[UsageBucket], float], bool]] = {
    "requests": (lambda bucket: bucket.requests, True),
    "prompt_tokens": (lambda bucket: bucket.prompt_tokens, True),
    "completion_tokens": (lambda bucket: bucket.completion_tokens, True),
    "total_tokens": (lambda bucket: bucket.total_tokens, True),
    "cost": (lambda bucket: bucket.cost, False),
    "kWh": (lambda bucket: bucket.impacts.kWh, False),
    "kgCO2eq": (lambda bucket: bucket.impacts.kgCO2eq, False),
}
DAILY_TABLES = (
    ("REQUESTS AND TOKENS PER DAY", ("requests", "prompt_tokens", "completion_tokens", "total_tokens")),
    ("COST AND IMPACT SCORES PER DAY", ("cost", "kWh", "kgCO2eq")),
)
FILTERS = (("endpoint", "endpoint", "endpoint", str), ("model", "router_name", "model", str), ("key", "token_id", "key_id", int))


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = Field(..., description="OpenGateLLM PostgreSQL URL (postgresql+asyncpg://...), credentials optional.")
    postgres_user: str = Field(default="", description="Injected into POSTGRES_URL when it carries no user.")
    postgres_password: str = Field(default="", description="Injected into POSTGRES_URL when it carries no password.")
    langfuse_public_key: str = Field(..., description="Langfuse project public key (pk-lf-...).")
    langfuse_secret_key: str = Field(..., description="Langfuse project secret key (sk-lf-...).")
    langfuse_base_url: str = Field(..., validation_alias=AliasChoices("langfuse_base_url", "langfuse_host"))
    langfuse_environment: str | None = Field(default=None, description="Langfuse environment, must match the one the API writes to.")

    def database_url(self) -> URL:
        """Keep the credentials out of POSTGRES_URL: SQLAlchemy escapes them, no percent-encoding needed."""
        url = make_url(self.postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1))
        if self.postgres_user and not url.username:
            url = url.set(username=self.postgres_user)
        if self.postgres_password and not url.password:
            url = url.set(password=self.postgres_password)
        return url


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-id", type=int, required=True, help="User id whose usage is compared.")
    parser.add_argument("--days", type=int, default=30, help="Window size in days, ending now (default 30).")
    parser.add_argument("--tolerance", type=float, default=1e-6, help="Relative tolerance on the float metrics (cost, impacts).")
    return parser.parse_args()


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


def paired_columns(postgres: UsageBucket | None, langfuse: UsageBucket | None, names: tuple[str, ...], tolerance: float) -> tuple[list[str], bool]:
    """One `postgres` then one `langfuse` cell per metric, plus whether they all match."""
    left, right = postgres or empty_bucket(), langfuse or empty_bucket()
    cells, matching = [], True
    for name in names:
        read, integer = METRICS[name]
        postgres_value, langfuse_value = read(left), read(right)
        cells += [format_value(postgres_value, integer), format_value(langfuse_value, integer)]
        matching = matching and matches(postgres_value, langfuse_value, integer, tolerance)
    return cells, matching


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    """Aligned plain-text table: header, rule, rows. First column left-aligned, the others right-aligned."""
    widths = [max([len(header), *(len(row[index]) for row in rows)]) for index, header in enumerate(headers)]

    def line(cells: list[str]) -> str:
        padded = (cell.ljust(width) if index == 0 else cell.rjust(width) for index, (cell, width) in enumerate(zip(cells, widths)))
        return "  ".join(padded).rstrip()

    return "\n".join([line(headers), "  ".join("-" * width for width in widths), *(line(row) for row in rows)])


def totals_of(buckets: list[UsageBucket]) -> UsageBucket:
    now = datetime.now(tz=UTC)
    return UsageBucket(
        start_time=now,
        end_time=now,
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


async def top_values(session: AsyncSession, column: str, user_id: int, start_time: datetime, end_time: datetime) -> list[str]:
    """Most used endpoints / router names / key ids of that user, read from Postgres."""
    query = text(
        f"SELECT {column} AS value FROM usage "  # noqa: S608 - column is a literal from the caller
        "WHERE user_id = :user_id AND status >= 200 AND status < 300 AND created >= :start_time AND created <= :end_time "
        f"AND {column} IS NOT NULL GROUP BY {column} ORDER BY count(*) DESC LIMIT :limit"
    )
    parameters = {"user_id": user_id, "start_time": start_time, "end_time": end_time, "limit": TOP_FILTER_VALUES}
    result = await session.execute(query, parameters)
    return [row.value for row in result.all()]


async def compare_days(
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

    matching = True
    for title, names in DAILY_TABLES:
        rows = []
        for day in sorted(set(postgres_days) | set(langfuse_days)):
            postgres_bucket, langfuse_bucket = postgres_days.get(day), langfuse_days.get(day)
            presence = "both" if postgres_bucket and langfuse_bucket else ("postgres only" if postgres_bucket else "langfuse only")
            cells, day_matching = paired_columns(postgres_bucket, langfuse_bucket, names, arguments.tolerance)
            rows.append([str(day), *cells, presence, "ok" if day_matching else "MISMATCH"])
            matching = matching and day_matching
        headers = ["day", *(f"{name} {side}" for name in names for side in ("pg", "lf")), "presence", "status"]
        logger.info(f"{title}\n" + render_table(headers, rows))

    postgres_totals, langfuse_totals = totals_of(postgres_buckets), totals_of(langfuse_buckets)
    summary_rows = [["days covered", str(len(postgres_days)), str(len(langfuse_days)), "", "ok" if len(postgres_days) == len(langfuse_days) else "MISMATCH"]]  # fmt: off
    for name, (read, integer) in METRICS.items():
        left, right = read(postgres_totals), read(langfuse_totals)
        delta = f"{right - left:+}" if integer else f"{right - left:+.6f}"
        status = "ok" if matches(left, right, integer, arguments.tolerance) else "MISMATCH"
        summary_rows.append([name, format_value(left, integer), format_value(right, integer), delta, status])
    logger.info("SUMMARY OVER THE WINDOW\n" + render_table(["metric", "postgres", "langfuse", "delta", "status"], summary_rows))

    return matching


async def compare_filters(
    session: AsyncSession,
    postgres_repository: PostgresUsageRepository,
    langfuse_repository: LangfuseUsageRepository,
    arguments: argparse.Namespace,
    start_time: datetime,
    end_time: datetime,
) -> bool:
    """Per-endpoint / per-model / per-key totals: the filters a bucket total can match while they return nothing."""
    matching = True
    rows = []
    for label, column, keyword, cast in FILTERS:
        for value in await top_values(session, column, arguments.user_id, start_time, end_time):
            filtered_postgres, filtered_langfuse = await read_both(
                postgres_repository,
                langfuse_repository,
                user_id=arguments.user_id,
                start_time=start_time,
                end_time=end_time,
                **{keyword: cast(value)},
            )
            left, right = totals_of(filtered_postgres), totals_of(filtered_langfuse)
            cells, filter_matching = paired_columns(left, right, ("requests", "total_tokens"), arguments.tolerance)
            matching = matching and filter_matching
            rows.append([label, str(value), *cells, "ok" if filter_matching else "MISMATCH"])

    headers = ["filter", "value", "requests pg", "requests lf", "tokens pg", "tokens lf", "status"]
    logger.info("FILTERS — trace name, providedModelName, key_id tag\n" + render_table(headers, rows))
    return matching


async def main() -> None:
    arguments = parse_arguments()
    config = Config()
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(days=arguments.days)

    client = Langfuse(
        public_key=config.langfuse_public_key,
        secret_key=config.langfuse_secret_key,
        base_url=config.langfuse_base_url,
        environment=config.langfuse_environment,
        tracing_enabled=False,
    )
    if not client.auth_check():
        raise RuntimeError(f"Langfuse authentication failed against {config.langfuse_base_url}")

    engine = create_async_engine(config.database_url(), pool_pre_ping=True)
    try:
        async with AsyncSession(engine) as session:
            postgres_repository = PostgresUsageRepository(postgres_session=session, background_tasks=BackgroundTasks())
            langfuse_repository = LangfuseUsageRepository(client=client)
            logger.info(f"Comparing user {arguments.user_id} from {start_time.isoformat()} to {end_time.isoformat()}")
            matching = await compare_days(postgres_repository, langfuse_repository, arguments, start_time, end_time)
            matching = await compare_filters(session, postgres_repository, langfuse_repository, arguments, start_time, end_time) and matching
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
