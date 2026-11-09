import logging
from typing import Annotated

from pydantic import Field, StringConstraints, field_validator

from api.infrastructure.configuration._validationerrors import HiddenInputSchema, custom_validation_error


@custom_validation_error
class PostgresDependency(HiddenInputSchema):
    """
    Postgres is a required dependency of OpenGateLLM. In this section, you can pass all postgres python SDK arguments, see https://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-apihttps://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-api for more information.
    Only the `url` argument is required. The connection URL must use the asynchronous scheme, `postgresql+asyncpg://`. If you provide a standard `postgresql://` URL, it will be automatically converted to use asyncpg.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(pattern=r"^postgresql", description="PostgreSQL connection url.", examples=["postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"])]  # fmt: off

    @field_validator("url", mode="after")
    def force_async(cls, url):
        if url.startswith("postgresql://"):
            logging.warning(msg="PostgreSQL connection must be async, force asyncpg connection.")
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        return url


@custom_validation_error
class LangfuseDependency(HiddenInputSchema):
    """
    Langfuse is an optional dependency of OpenGateLLM. Langfuse is used for LLM observability and tracing.
    In this section, you can pass all Langfuse client arguments, see https://python.reference.langfuse.com/langfuse for more information.
    """

    public_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Langfuse public key.", examples=["pk-lf-..."])]  # fmt: off
    secret_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Langfuse secret key.", examples=["sk-lf-..."])]  # fmt: off
    base_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(default="http://localhost:3000", description="Langfuse server URL.", examples=["http://localhost:3000"])]  # fmt: off


@custom_validation_error
class SentryDependency(HiddenInputSchema):
    """
    Sentry is an optional dependency of OpenGateLLM. Sentry helps you identify, diagnose, and fix errors in real-time.
    In this section, you can pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information.
    """


@custom_validation_error
class RedisDependency(HiddenInputSchema):
    """
    Redis is a required dependency of OpenGateLLM. Redis is used to store rate limiting counters and inflight gauges.
    Pass all `from_url()` method arguments of `redis.asyncio.connection.ConnectionPool` class, see https://redis.readthedocs.io/en/stable/connections.html#redis.asyncio.connection.ConnectionPool.from_url for more information.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(pattern=r"^redis://", description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])]  # fmt: off


@custom_validation_error
class Dependencies(HiddenInputSchema):
    langfuse: Annotated[LangfuseDependency | None, Field(default=None, description="See the [LangfuseDependency section](#langfusedependency) for more information.")]  # fmt: off
    postgres: Annotated[PostgresDependency, Field(description="Postgres is a required dependency of OpenGateLLM to store API data.")]  # fmt: off
    redis: Annotated[RedisDependency, Field(description="Redis is a required dependency for the API to store rate limiting counters and inflight gauges. It is an optional dependency for the Playground to use as stage manage (see [Reflex documentation](https://reflex.dev/docs/api-reference/config/)).")]  # fmt: off
    sentry: Annotated[SentryDependency | None, Field(default=None, description="Sentry is an optional dependency of OpenGateLLM. Sentry helps you identify, diagnose, and fix errors in real-time.")]  # fmt: off
