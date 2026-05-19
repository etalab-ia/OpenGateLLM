from enum import StrEnum
from functools import wraps
import logging
import os
from pathlib import Path
import re
from typing import Annotated, Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, constr, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

from api.domain.provider.entities import HostingZone, ProviderType
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.elasticsearch import ElasticsearchIndexLanguage
from api.schemas.core.models import Metric
from api.schemas.models import ModelType
from api.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, RouterName

# utils ----------------------------------------------------------------------------------------------------------------------------------------------


def custom_validation_error(suffix: str = ""):
    """
    Decorator to override Pydantic ValidationError to change error message.

    Args:
        url(Optional[str]): override Pydantic documentation URL by provided URL. If not provided, the error message will be the same as the original error message.
    """

    class ValidationError(Exception):
        def __init__(
            self, exc: PydanticValidationError, cls: BaseModel, base_url: str = "https://docs.opengatellm.org/configuration/configuration_file"
        ):
            super().__init__()
            error_content = exc.errors()

            def resolve_model_for_error(model: type[BaseModel], loc: tuple[Any, ...]):
                current_model = model
                documentation_url = base_url

                for idx, part in enumerate(loc):
                    if not isinstance(part, str):
                        continue
                    if part not in current_model.__pydantic_fields__:
                        break

                    field_info = current_model.__pydantic_fields__[part]

                    annotation = field_info.annotation
                    next_model = None
                    origin = get_origin(annotation)
                    args = get_args(annotation)
                    candidates = args if origin is not None else (annotation,)

                    for candidate in candidates:
                        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                            next_model = candidate
                            break

                    if next_model is None:
                        break

                    current_model = next_model
                    documentation_url = f"{base_url}#{current_model.__name__.lower()}{suffix}"

                return documentation_url

            message = str(exc)
            for error in error_content:
                loc = tuple(error.get("loc", ()))
                documentation_url = resolve_model_for_error(cls, loc)
                original_line = f"    For further information visit {error['url']}"
                replacement_line = f"    For further information visit {documentation_url}"
                message = message.replace(original_line, replacement_line, 1)

            self.message = message

        def __str__(self):
            return self.message

    def decorator(cls: type[BaseModel]):
        original_init = cls.__init__

        @wraps(original_init)
        def new_init(self, **data):
            try:
                original_init(self, **data)
            except PydanticValidationError as e:
                raise ValidationError(exc=e, cls=cls) from None  # hide previous traceback

        cls.__init__ = new_init
        return cls

    return decorator


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


# models ---------------------------------------------------------------------------------------------------------------------------------------------


@custom_validation_error()
class ModelProvider(ConfigBaseModel):
    type: Annotated[ProviderType, Field(..., description="Model provider type.")]
    url: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, description="Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI).")]  # fmt: off
    key: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1), Field(default=None, description="Model provider API key.")]  # fmt: off
    timeout: Annotated[int, Field(default=DEFAULT_TIMEOUT, description="Timeout for the model provider requests, after user receive an 503 error (model is too busy).")]  # fmt: off
    model_name: Annotated[str, Field(..., description="Model name from the model provider.")]  # fmt: off
    model_hosting_zone: Annotated[HostingZone, Field(default=HostingZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai")]  # fmt: off
    model_total_params: Annotated[int, Field(default=0, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai")]  # fmt: off
    model_active_params: Annotated[int, Field(default=0, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai")]  # fmt: off
    qos_metric: Annotated[Metric | None, Field(default=None, description="The metric to use for the quality of service policy. If not provided, no QoS policy is applied.")]  # fmt: off
    qos_limit: Annotated[float | None, Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.")]  # fmt: off

    @model_validator(mode="after")
    def format_provider(self):
        if self.qos_metric is not None and self.qos_limit is None:
            raise ValueError("QoS value is required if QoS metric is provided.")

        if self.url is None:
            if self.type == ProviderType.ALBERT:
                self.url = "https://albert.api.etalab.gouv.fr/"
            elif self.type == ProviderType.MISTRAL:
                self.url = "https://albert.api.etalab.gouv.fr/"
            elif self.type == ProviderType.OPENAI:
                self.url = "https://api.openai.com/"
            else:
                raise ValueError("URL is required for this model provider type.")

        elif not self.url.endswith("/"):
            self.url = f"{self.url}/"

        return self


@custom_validation_error()
class Model(ConfigBaseModel):
    """
    In the model section, you define a list of models (routers and providers). These models are only used for the initial bootstrap of the API.
    The model section of the configuration is ignored if any models are already registered in the database.
    """

    name: constr(strip_whitespace=True, min_length=1, max_length=64) = Field(..., description="Unique name exposed to clients when selecting the model.", examples=["gpt-4o"])  # fmt: off
    type: ModelType = Field(..., description="Type of the model. It will be used to identify the model type.", examples=["text-generation"])  # fmt: off
    aliases: list[constr(strip_whitespace=True, min_length=1, max_length=64)] = Field(default_factory=list, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]], json_schema_extra={"default": []})  # fmt: off
    load_balancing_strategy: RouterLoadBalancingStrategy = Field(default=RouterLoadBalancingStrategy.SHUFFLE, description="Routing strategy for load balancing between providers of the model.", examples=["least_busy"])  # fmt: off
    cost_prompt_tokens: float = Field(default=0.0, ge=0.0, description="Model costs prompt tokens for user budget computation. The cost is by 1M tokens.", examples=[0.1])  # fmt: off
    cost_completion_tokens: float = Field(default=0.0, ge=0.0, description="Model costs completion tokens for user budget computation. The cost is by 1M tokens. Set to `0.0` to disable budget computation for this model.", examples=[0.1])  # fmt: off
    providers: list[ModelProvider] = Field(..., description="API providers of the model. If there are multiple providers, the model will be load balanced between them according to the routing strategy. The different models have to the same type.")  # fmt: off

    @model_validator(mode="after")
    def validate_provider_type(self):
        for provider in self.providers:
            if not provider.type.is_compatible_with(router_type=self.type):
                raise ValueError(f"Provider type {provider.type.value} is not compatible with model type {self.type.value}")

        return self


# dependencies ---------------------------------------------------------------------------------------------------------------------------------------


class ParserType(StrEnum):
    ALBERT = "albert"
    MARKER = "marker"


class DependencyType(StrEnum):
    ALBERT = "albert"
    CELERY = "celery"
    ELASTICSEARCH = "elasticsearch"
    MARKER = "marker"
    POSTGRES = "postgres"
    REDIS = "redis"
    SENTRY = "sentry"


@custom_validation_error()
class AlbertDependency(ConfigBaseModel):
    """
    **[DEPRECATED]**
    """

    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://albert.api.etalab.gouv.fr", description="Albert API url.")  # fmt: off
    headers: dict[str, str] = Field(default_factory=dict, description="Albert API request headers.", examples=[{"Authorization": "Bearer my-api-key"}], json_schema_extra={"default": {}})  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, description="Timeout for the Albert API requests.", examples=[10])  # fmt: off


@custom_validation_error()
class CeleryDependency(ConfigBaseModel):
    """
    **[DEPRECATED]**
    """

    broker_url: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Celery broker url like Redis (redis://) or RabbitMQ (amqp://). If not provided, use redis dependency as broker.")  # fmt: off
    result_backend: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Celery result backend url. If not provided, use redis dependency as result backend.")  # fmt: off
    timezone: str = Field(default="UTC", description="Timezone.", examples=["UTC"])  # fmt: off
    enable_utc: bool = Field(default=True, description="Enable UTC.", examples=[True])  # fmt: off


@custom_validation_error()
class ElasticsearchDependency(ConfigBaseModel):
    """
    Elasticsearch is an optional dependency of OpenGateLLM. Elasticsearch is used as a vector store. If this dependency is provided, all documents endpoint are enabled.
    Pass all arguments of `elasticsearch.Elasticsearch` class, see https://elasticsearch-py.readthedocs.io/en/latest/api/elasticsearch.html for more information.
    Other arguments declared below are used to configure the Elasticsearch index.
    """

    index_name: constr(strip_whitespace=True, min_length=1) = Field(default="opengatellm", description="Name of the Elasticsearch index.", examples=["my_index"])  # fmt: off
    index_language: ElasticsearchIndexLanguage = Field(default=ElasticsearchIndexLanguage.ENGLISH, description="Language of the Elasticsearch index.", examples=[ElasticsearchIndexLanguage.ENGLISH.value])  # fmt: off
    number_of_shards: int = Field(default=12, ge=1, le=75, description="Number of shards for the Elasticsearch index.", examples=[4])  # fmt: off
    number_of_replicas: int = Field(default=1, ge=0, description="Number of replicas for the Elasticsearch index.", examples=[1])  # fmt: off


@custom_validation_error()
class MarkerDependency(ConfigBaseModel):
    """
    **[DEPRECATED]**
    """

    url: constr(strip_whitespace=True, min_length=1) = Field(..., description="Marker API url.")  # fmt: off
    headers: dict[str, str] = Field(default_factory=dict, description="Marker API request headers.", examples=[{"Authorization": "Bearer my-api-key"}], json_schema_extra={"default": {}})  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, description="Timeout for the Marker API requests.", examples=[10])  # fmt: off


@custom_validation_error()
class PostgresDependency(ConfigBaseModel):
    """
    Postgres is a required dependency of OpenGateLLM. In this section, you can pass all postgres python SDK arguments, see https://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-apihttps://docs.sqlalchemy.org/en/21/core/engines.html#engine-creation-api for more information.
    Only the `url` argument is required. The connection URL must use the asynchronous scheme, `postgresql+asyncpg://`. If you provide a standard `postgresql://` URL, it will be automatically converted to use asyncpg.
    """

    url: constr(strip_whitespace=True, min_length=1) = Field(..., pattern=r"^postgresql", description="PostgreSQL connection url.", examples=["postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"])  # fmt: off

    @field_validator("url", mode="after")
    def force_async(cls, url):
        if url.startswith("postgresql://"):
            logging.warning(msg="PostgreSQL connection must be async, force asyncpg connection.")
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        return url


@custom_validation_error()
class LangfuseDependency(ConfigBaseModel):
    """
    Langfuse is an optional dependency of OpenGateLLM. Langfuse is used for LLM observability and tracing.
    In this section, you can pass all Langfuse client arguments, see https://python.reference.langfuse.com/langfuse for more information.
    """

    public_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(..., description="Langfuse public key.", examples=["pk-lf-..."])  # fmt: off
    secret_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(..., description="Langfuse secret key.", examples=["sk-lf-..."])  # fmt: off
    base_url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default="http://localhost:3000", description="Langfuse server URL.", examples=["http://localhost:3000"])  # fmt: off


@custom_validation_error()
class SentryDependency(ConfigBaseModel):
    """
    Sentry is an optional dependency of OpenGateLLM. Sentry helps you identify, diagnose, and fix errors in real-time.
    In this section, you can pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information.
    """

    pass
    # All args of pydantic sentry client is allowed


@custom_validation_error()
class RedisDependency(ConfigBaseModel):
    """
    Redis is a required dependency of OpenGateLLM. Redis is used to store rate limiting counters and performance metrics.
    Pass all `from_url()` method arguments of `redis.asyncio.connection.ConnectionPool` class, see https://redis.readthedocs.io/en/stable/connections.html#redis.asyncio.connection.ConnectionPool.from_url for more information.
    """

    url: constr(strip_whitespace=True, min_length=1) = Field(..., pattern=r"^redis://", description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])  # fmt: off


class EmptyDependency(ConfigBaseModel):
    pass


@custom_validation_error()
class Dependencies(ConfigBaseModel):
    albert: AlbertDependency | None = Field(default=None, json_schema_extra={"deprecated": True})  # fmt: off
    celery: CeleryDependency | None = Field(default=None, json_schema_extra={"deprecated": True})  # fmt: off
    elasticsearch: ElasticsearchDependency | None = Field(default=None, description="Elasticsearch is an optional dependency of OpenGateLLM. Elasticsearch is used as a vector store. If this dependency is provided, all documents endpoint are enabled.")  # fmt: off
    langfuse: LangfuseDependency | None = Field(default=None, description="See the [LangfuseDependency section](#langfusedependency) for more information.")  # fmt: off
    marker: MarkerDependency | None = Field(default=None, json_schema_extra={"deprecated": True})  # fmt: off
    postgres: PostgresDependency = Field(..., description="Postgres is a required dependency of OpenGateLLM to store API data.")  # fmt: off
    redis: RedisDependency  = Field(..., description="Redis is a required dependency of OpenGateLLM to store rate limiting counters and performance metrics.")  # fmt: off
    sentry: SentryDependency | None = Field(default=None, description="Sentry is an optional dependency of OpenGateLLM. Sentry helps you identify, diagnose, and fix errors in real-time.")  # fmt: off

    @model_validator(mode="after")
    def complete_celery(self):
        if self.celery is not None:
            if self.celery.broker_url is None:
                self.celery.broker_url = self.redis.url
            if self.celery.result_backend is None:
                self.celery.result_backend = self.redis.url

            logging.info("Celery queuing is enabled.")

        return self

    @model_validator(mode="after")
    def validate_dependencies(self):
        """
        Check if only one dependency of each family is provided. For example, Elasticsearch can be used, but not both.

        The parser dependency can be Albert or Marker, it is converted into a single attribute called "parser".
        """

        def create_attribute(name: str, type: StrEnum, values: Any):
            candidates = [item for item in type if getattr(values, item.value) is not None]

            # Ensure only one dependency of this family is defined
            if len(candidates) > 1:
                raise ValueError(f"Only one {type.__name__} is allowed (provided: {', '.join(c.value for c in candidates)}).")

            # If no dependency is provided, set the attribute to None
            if len(candidates) == 0:
                setattr(values, name, None)
            else:
                chosen_enum = candidates[0]
                dep_obj = getattr(values, chosen_enum.value)

                # Add a `type` field on the dependency object to remember its family (string form)
                setattr(dep_obj, "type", chosen_enum)

                # Expose the dependency under the generic name (parser, ...)
                setattr(values, name, dep_obj)

                # Clean up specific attributes
                for item in type:
                    if item != chosen_enum and hasattr(values, item.value):
                        delattr(values, item.value)

            return values

        self = create_attribute(name="parser", type=ParserType, values=self)

        return self


# settings -------------------------------------------------------------------------------------------------------------------------------------------
class LimitingStrategy(StrEnum):
    MOVING_WINDOW = "moving_window"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class Tokenizer(StrEnum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


@custom_validation_error()
class Settings(ConfigBaseModel):
    """
    General settings configuration fields.
    """

    # general
    disabled_routers: list[RouterName] = Field(default_factory=list, description="Disabled routers to limits services of the API.", examples=[["embeddings"]], json_schema_extra={"default": []})  # fmt: off
    hidden_routers: list[RouterName] = Field(default_factory=list, description="Routers are enabled but hidden in the swagger and the documentation of the API.", examples=[["admin"]], json_schema_extra={"default": []})  # fmt: off
    app_title: str = Field(default=DEFAULT_APP_NAME, description="Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API"])  # fmt: off

    # routing
    routing_max_retries: int = Field(default=3, ge=1, description="Maximum number of retries for routing tasks.")  # fmt: off
    routing_retry_countdown: int = Field(default=3, ge=1, description="Number of seconds before retrying a failed routing task.")  # fmt: off
    routing_max_priority: int = Field(default=4, ge=0, le=10, description="Maximum allowed priority in routing tasks.")  # fmt: off

    # usage tokenizer
    usage_tokenizer: Tokenizer = Field(default=Tokenizer.TIKTOKEN_GPT2, description="Tokenizer used to compute usage of the API.")  # fmt: off

    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Logging level of the API.")  # fmt: off
    log_format: str = Field(default="[%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s", description="Logging format of the API.")  # fmt: off

    # swagger
    swagger_summary: str = Field(default="OpenGateLLM connect to your models. You can configuration this swagger UI in the configuration file, like hide routes or change the title.", description="Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API description."])  # fmt: off
    swagger_version: str = Field(default="latest", description="Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["2.5.0"])  # fmt: off
    swagger_description: str = Field(default="[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)", description="Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)"])  # fmt: off
    swagger_contact: dict | None = Field(default=None, description="Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_license_info: dict = Field(default={"name": "MIT Licence", "identifier": "MIT", "url": "https://raw.githubusercontent.com/etalab-ia/opengatellm/refs/heads/main/LICENSE"}, description="Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_terms_of_service: str | None = Field(default=None, description="A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL.", examples=["https://example.com/terms-of-service"])  # fmt: off
    swagger_openapi_tags: list[dict[str, str | dict[str, str]]] = Field(default_factory=list, description="OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", json_schema_extra={"default": []})  # fmt: off
    swagger_openapi_url: str = Field(default="/openapi.json", pattern=r"^/", description="OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_docs_url: str = Field(default="/docs", pattern=r"^/", description="Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_redoc_url: str = Field(default="/redoc", pattern=r"^/", description="Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off

    # auth
    auth_master_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(default="changeme", description="[DEPRECATED] Master key for the API. It should be a random string with at least 32 characters. This key has all permissions and cannot be modified or deleted. This key is used to create the first role and the first user.", deprecated=True)  # fmt: off
    auth_secret_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = Field(default=None, description="Secret key for the API. It should be a random string with at least 32 characters. This key is used to encrypt user tokens, watch out if you modify the secret key, you'll need to update all user API keys. If not provided, the master key will be used.")  # fmt: off
    auth_bootsrap_admin_username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)] = Field(default="admin", description="Username of the admin user created at the first startup.")  # fmt: off
    auth_bootsrap_admin_password: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=72)] = Field(default="changeme", description="Password of the admin user created at the first startup.")  # fmt: off
    auth_key_max_expiration_days: int | None = Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")  # fmt: off
    auth_playground_session_duration: int = Field(default=3600, ge=1, description="Duration of the playground postgres_session in seconds.")  # fmt: off

    # rate_limiting
    rate_limiting_strategy: LimitingStrategy = Field(default=LimitingStrategy.FIXED_WINDOW, description="Rate limiting strategy for the API.")  # fmt: off

    # monitoring
    monitoring_postgres_enabled: bool = Field(default=True, description="If true, the log usage will be written in the PostgreSQL database.")  # fmt: off
    monitoring_prometheus_enabled: bool = Field(default=True, description="If true, Prometheus metrics will be exposed in the `/metrics` endpoint.")  # fmt: off

    # vector_store
    vector_store_model: str | None = Field(default=None, description="Model used to vectorize the text in the vector store database. Is required if a vector store dependency is provided (Elasticsearch). This model must be defined in the `models` section and have type `text-embeddings-inference`.")  # fmt: off

    # document_parsing
    document_parsing_max_concurrent: int = Field(default=10, ge=1, description="Maximum number of concurrent document parsing tasks per worker.")  # fmt: off

    front_url: str = Field(default="http://localhost:8501", description="Front-end URL for the application.")

    @model_validator(mode="after")
    def validate_model(self) -> Any:
        if self.auth_secret_key is None:
            logging.warning("The 'auth_secret_key' setting is not set. Falling back to 'auth_master_key' for signing API keys.")  # fmt: off
            logging.warning("Please set 'auth_secret_key' to a dedicated secret value in your 'config.yaml' file.")  # fmt: off
            logging.warning("The 'auth_master_key' fallback will be removed in v1.0.0, where 'auth_secret_key' will become mandatory and 'auth_master_key' will no longer be used as a signing secret.")  # fmt: off
            self.auth_secret_key = self.auth_master_key

        return self


# load config ----------------------------------------------------------------------------------------------------------------------------------------
@custom_validation_error()
class ConfigFile(ConfigBaseModel):
    """
    Configuration file is composed of 3 sections, models:
    - `models`: to declare models API exposed to the API.
    - `dependencies`: to declare both required plugins for the API (e.g. PostgreSQL, Redis) and optional ones (e.g. Elasticsearch).
    - `settings`: to configure the API.

    :::warnings
    We don't recommend to use the configuration file to declare models, prefer to use the API to declare models, by endpoints or on the Playground UI (see [Models configuration](/getting-started/models/)).
    :::
    """

    models: list[Model] = Field(default_factory=list, description="Models used by the API.")  # fmt: off
    dependencies: Dependencies = Field(default_factory=Dependencies, description="Dependencies used by the API.")  # fmt: off
    settings: Settings = Field(default_factory=Settings, description="General settings configuration fields.")  # fmt: off

    @field_validator("settings", mode="before")
    def set_default_settings(cls, settings) -> Any:
        if settings is None:
            return Settings()
        return settings

    @model_validator(mode="after")
    def validate_models(self) -> Any:
        # get all models and aliases for each model type
        models = {"all": []}
        for model_type in ModelType:
            models[model_type.value] = []
            for model in self.models:
                if model.type == model_type:
                    model_names_and_aliases = [alias for alias in model.aliases] + [model.name]
                    models[model_type.value].extend(model_names_and_aliases)

        # build the complete list of all models
        for model_type in ModelType:
            models["all"].extend(models[model_type.value])

        # check for interdependencies
        if self.dependencies.elasticsearch and self.settings.vector_store_model:
            assert self.settings.vector_store_model in models["all"], "Vector store model must be defined in models section."
            assert self.settings.vector_store_model in models[ModelType.TEXT_EMBEDDINGS_INFERENCE.value], f"The vector store model must have type {ModelType.TEXT_EMBEDDINGS_INFERENCE}."  # fmt: off

        return self


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    # config
    config_file: str = "config.yml"
    prometheus_multiproc_dir: str = "/tmp/prometheus_multiproc"

    @field_validator("config_file", mode="before")
    def config_file_exists(cls, config_file):
        assert Path(config_file).is_file(), f"Config file ({config_file}) not found."
        return config_file

    @model_validator(mode="after")
    def setup_config(self) -> Any:
        with open(file=self.config_file) as file:
            lines = file.readlines()

        # remove commented lines
        uncommented_lines = [line for line in lines if not line.lstrip().startswith("#")]

        # replace environment variables
        file_content = self.replace_environment_variables(file_content="".join(uncommented_lines))
        # load config
        config = ConfigFile(**yaml.safe_load(stream=file_content))

        self.models = config.models
        self.dependencies = config.dependencies
        self.settings = config.settings

        return self

    @classmethod
    def replace_environment_variables(cls, file_content):
        env_variable_pattern = re.compile(r"\${([A-Z0-9_]+)(:-[^}]*)?}")

        def replace_env_var(match):
            env_variable_definition = match.group(0)
            env_variable_name = match.group(1)
            default_env_variable_value = match.group(2)[2:] if match.group(2) else None

            env_variable_value = os.getenv(env_variable_name)

            if env_variable_value is not None and env_variable_value != "":
                return env_variable_value
            elif default_env_variable_value is not None:
                return default_env_variable_value
            else:
                logging.warning(f"Environment variable {env_variable_name} not found or empty to replace {env_variable_definition}.")
                return env_variable_definition

        file_content = env_variable_pattern.sub(replace_env_var, file_content)

        return file_content
