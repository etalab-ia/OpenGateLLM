from enum import Enum
from functools import wraps
import logging
import os
from pathlib import Path
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, constr, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings
import yaml

from api.schemas.admin.providers import ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.routers import RouterLoadBalancingStrategy
from api.schemas.core.metrics import Metric
from api.schemas.models import ModelType
from api.utils.variables import DEFAULT_APP_NAME, DEFAULT_TIMEOUT, ROUTER__ADMIN, ROUTER__AUTH, ROUTERS

# utils ----------------------------------------------------------------------------------------------------------------------------------------------


def custom_validation_error(url: str | None = None):
    """
    Decorator to override Pydantic ValidationError to change error message.

    Args:
        url(Optional[str]): override Pydantic documentation URL by provided URL. If not provided, the error message will be the same as the original error message.
    """

    class ValidationError(Exception):
        def __init__(self, exc: PydanticValidationError, cls: BaseModel, url: str):
            super().__init__()
            error_count = exc.error_count()
            error_content = exc.errors()
            message = f"{error_count} validation error for {cls.__name__}\n"

            for error in error_content:
                url = url or error["url"]
                if error["type"] == "assertion_error":
                    message += f"{error["msg"]}\n"
                else:
                    if len(error["loc"]) > 0:
                        message += f"{error["loc"][0]}\n"
                    message += f"  {error["msg"]} [type={error["type"]}, input_value={error.get("input", "")}, input_type={type(error.get("input")).__name__}]\n"  # fmt: off
                    if len(error["loc"]) > 0:
                        description = cls.__pydantic_fields__[error["loc"][0]].description
                        if description:
                            message += f"\n  {description}\n"
                message += f"    For further information visit {url}\n\n"

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
                raise ValidationError(exc=e, cls=cls, url=url) from None  # hide previous traceback

        cls.__init__ = new_init
        return cls

    return decorator


class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


# models ---------------------------------------------------------------------------------------------------------------------------------------------


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#modelprovider")
class ModelProvider(ConfigBaseModel):
    type: ProviderType = Field(..., description="Model provider type.", examples=["openai"])  # fmt: off
    url: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI).", examples=["https://api.openai.com"])  # fmt: off
    key: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Model provider API key.", examples=["sk-1234567890"])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Timeout for the model provider requests, after user receive an 500 error (model is too busy).", examples=[10])  # fmt: off
    model_name: constr(strip_whitespace=True, min_length=1) = Field(..., description="Model name from the model provider.", examples=["gpt-4o"])  # fmt: off
    model_carbon_footprint_zone: ProviderCarbonFootprintZone = Field(default=ProviderCarbonFootprintZone.WOR, description="Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai", examples=["WOR"])  # fmt: off
    model_carbon_footprint_total_params: int | None = Field(default=None, ge=0, description="Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai", examples=[8])  # fmt: off
    model_carbon_footprint_active_params: int | None = Field(default=None, ge=0, description="Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai", examples=[8])  # fmt: off
    qos_metric: Metric | None = Field(default=None, description="The metric to use for the quality of service. If not provided, no QoS policy is applied.", examples=[Metric.INFLIGHT.value])  # fmt: off
    qos_limit: float | None = Field(default=None, ge=0.0, description="The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc.", examples=[0.5])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#model")
class Model(ConfigBaseModel):
    """
    In the models section, you define a list of models. Each model is a set of API providers for that model. Users will access the models specified in
    this section using their *name*. Load balancing is performed between the different providers of the requested model. All providers in a model must
    serve the same type of model (text-generation or text-embeddings-inference, etc.). We recommend that all providers of a model serve exactly the same
    model, otherwise users may receive responses of varying quality. For embedding models, the API verifies that all providers output vectors of the
    same dimension. You can define the load balancing strategy between the model's providers. By default, it is random.

    For more information to configure model providers, see the [ModelProvider section](#modelprovider).
    """

    name: constr(strip_whitespace=True, min_length=1, max_length=64) = Field(..., description="Unique name exposed to clients when selecting the model.", examples=["gpt-4o"])  # fmt: off
    type: ModelType = Field(..., description="Type of the model. It will be used to identify the model type.", examples=["text-generation"])  # fmt: off
    aliases: list[constr(strip_whitespace=True, min_length=1, max_length=64)] = Field(default_factory=list, description="Aliases of the model. It will be used to identify the model by users.", examples=[["model-alias", "model-alias-2"]])  # fmt: off
    load_balancing_strategy: RouterLoadBalancingStrategy = Field(default=RouterLoadBalancingStrategy.SHUFFLE, description="Routing strategy for load balancing between providers of the model.", examples=["least_busy"])  # fmt: off
    cost_prompt_tokens: float = Field(default=0.0, ge=0.0, description="Model costs prompt tokens for user budget computation. The cost is by 1M tokens.", examples=[0.1])  # fmt: off
    cost_completion_tokens: float = Field(default=0.0, ge=0.0, description="Model costs completion tokens for user budget computation. The cost is by 1M tokens. Set to `0.0` to disable budget computation for this model.", examples=[0.1])  # fmt: off
    providers: list[ModelProvider] = Field(..., description="API providers of the model. If there are multiple providers, the model will be load balanced between them according to the routing strategy. The different models have to the same type.")  # fmt: off


# dependencies ---------------------------------------------------------------------------------------------------------------------------------------


class ParserType(str, Enum):
    ALBERT = "albert"
    MARKER = "marker"


class VectorStoreType(str, Enum):
    ELASTICSEARCH = "elasticsearch"
    QDRANT = "qdrant"


class WebSearchEngineType(str, Enum):
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"


class DependencyType(str, Enum):
    ALBERT = "albert"
    CELERY = "celery"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    ELASTICSEARCH = "elasticsearch"
    QDRANT = "qdrant"
    MARKER = "marker"
    POSTGRES = "postgres"
    REDIS = "redis"
    SENTRY = "sentry"


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#albert")
class AlbertDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://albert.api.etalab.gouv.fr", description="Albert API url.")  # fmt: off
    headers: dict[str, str] = Field(default_factory=dict, description="Albert API request headers.", examples=[{"Authorization": "Bearer my-api-key"}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, description="Timeout for the Albert API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#celery")
class CeleryDependency(ConfigBaseModel):
    broker_url: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Celery broker url like Redis (redis://) or RabbitMQ (amqp://). If not provided, use redis dependency as broker.")  # fmt: off
    result_backend: constr(strip_whitespace=True, min_length=1) | None = Field(default=None, description="Celery result backend url. If not provided, use redis dependency as result backend.")  # fmt: off
    timezone: str = Field(default="UTC", description="Timezone.", examples=["UTC"])  # fmt: off
    enable_utc: bool = Field(default=True, description="Enable UTC.", examples=[True])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#brave")
class BraveDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://api.search.brave.com/res/v1/web/search", description="Brave API url.")  # fmt: off
    headers: dict[str, str] = Field(default_factory=dict, required = True, description="Brave API request headers.", examples=[{"X-Subscription-Token": "my-api-key"}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, description="Timeout for the Brave API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#duckduckgodependency")
class DuckDuckGoDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(default="https://api.duckduckgo.com/", description="DuckDuckGo API url.")  # fmt: off
    headers: dict[str, str] = Field(default_factory=dict, required = False, description="DuckDuckGo API request headers.", examples=[{}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, description="Timeout for the DuckDuckGo API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#elasticsearchdependency")
class ElasticsearchDependency(ConfigBaseModel):
    # All args of pydantic elastic client is allowed
    number_of_shards: int = Field(default=1, ge=1, description="Number of shards for the Elasticsearch index.", examples=[1])  # fmt: off
    number_of_replicas: int = Field(default=1, ge=0, description="Number of replicas for the Elasticsearch index.", examples=[1])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#qdrantdependency")
class QdrantDependency(ConfigBaseModel):
    @model_validator(mode="after")
    def force_rest(cls, values):
        if hasattr(values, "prefer_grpc") and values.prefer_grpc:
            logging.warning(msg="Qdrant does not support grpc for create index payload, force REST connection.")
            values.prefer_grpc = False

        return values


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#markerdependency")
class MarkerDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(..., description="Marker API url.")  # fmt: off
    headers: dict[str, str] = Field(default_factory=dict, description="Marker API request headers.", examples=[{"Authorization": "Bearer my-api-key"}])  # fmt: off
    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1, description="Timeout for the Marker API requests.", examples=[10])  # fmt: off


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#postgresdependency")
class PostgresDependency(ConfigBaseModel):
    # All args of pydantic postgres client is allowed
    url: constr(strip_whitespace=True, min_length=1) = Field(..., pattern=r"^postgresql", description="PostgreSQL connection url.", examples=["postgresql://postgres:changeme@localhost:5432/postgres"])  # fmt: off

    @field_validator("url", mode="after")
    def force_async(cls, url):
        if url.startswith("postgresql://"):
            logging.warning(msg="PostgreSQL connection must be async, force asyncpg connection.")
            url = url.replace("postgresql://", "postgresql+asyncpg://")

        return url


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#sentrydependency")
class SentryDependency(ConfigBaseModel):
    pass
    # All args of pydantic sentry client is allowed


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#redisdependency")
class RedisDependency(ConfigBaseModel):
    url: constr(strip_whitespace=True, min_length=1) = Field(..., pattern=r"^redis://", description="Redis connection url.", examples=["redis://:changeme@localhost:6379"])  # fmt: off


class ProConnect(ConfigBaseModel):
    client_id: str = Field(default="", description="Client identifier provided by ProConnect when you register your application in their dashboard. This value is public (it's fine to embed in clients) but must match the value configured in ProConnect.")  # fmt: off
    client_secret: str = Field(default="", description="Client secret provided by ProConnect at application registration. This value must be kept confidential — it's used by the server to authenticate with ProConnect during token exchange (do not expose it to browsers or mobile apps).")  # fmt: off
    server_metadata_url: str = Field(default="https://identite-sandbox.proconnect.gouv.fr/.well-known/openid-configuration", description="OpenID Connect discovery endpoint for ProConnect (server metadata). The SDK/flow uses this to discover authorization, token, and JWKS endpoints. Change to the production discovery URL when switching from sandbox to production.")  # fmt: off
    redirect_uri: str = Field(default="https://albert.api.etalab.gouv.fr/v1/auth/callback", description="Redirect URI where users are sent after successful ProConnect authentication. This URI must exactly match one of the redirect URIs configured in OpenGateLLM settings. It must be an HTTPS endpoint in production and is used to receive the authorization tokens from ProConnect.")  # fmt: off
    scope: str = Field(default="openid email given_name usual_name siret organizational_unit belonging_population chorusdt", description="Space-separated OAuth2/OpenID Connect scopes requested from ProConnect (for example: 'openid email given_name'). Scopes determine the information returned about the authenticated user; reduce scopes to the minimum necessary for privacy.")  # fmt: off
    allowed_domains: str = Field(default="localhost,gouv.fr", description="Comma-separated list of domains allowed to sign in via ProConnect (e.g. 'gouv.fr,example.com'). Only fronted on the specified domains will be allowed to authenticate using proconnect.")  # fmt: off
    default_role: str = Field(default="Freemium", description="Role automatically assigned to users created via ProConnect login on first sign-in. Set this to the role name you want new ProConnect users to receive (must exist in your roles configuration).")  # fmt: off


class EmptyDepencency(ConfigBaseModel):
    pass


@custom_validation_error(url="https://github.com/etalab-ia/albert-api/blob/main/docs/configuration.md#dependencies")
class Dependencies(ConfigBaseModel):
    albert: AlbertDependency | None = Field(default=None, description="If provided, Albert API is used to parse pdf documents. Cannot be used with Marker dependency concurrently. Pass arguments to call Albert API in this section.")  # fmt: off
    celery: CeleryDependency | None = Field(default=None, description="If provided, Celery is used to run tasks asynchronously with queues. Pass arguments to call Celery in this section.")  # fmt: off
    brave: BraveDependency | None = Field(default=None, description="If provided, Brave API is used to web search. Cannot be used with DuckDuckGo dependency concurrently. Pass arguments to call API in this section. All query parameters are supported, see https://api-dashboard.search.brave.com/app/documentation/web-search/query for more information.")  # fmt: off
    duckduckgo: DuckDuckGoDependency | None = Field(default=None, description="If provided, DuckDuckGo API is used to web search. Cannot be used with Brave dependency concurrently. Pass arguments to call API in this section. All query parameters are supported, see https://www.searchapi.io/docs/duckduckgo-api for more information.")  # fmt: off
    elasticsearch: ElasticsearchDependency | None = Field(default=None, description="Pass all elastic python SDK arguments, see https://elasticsearch-py.readthedocs.io/en/v9.0.2/api/elasticsearch.html#elasticsearch.Elasticsearch for more information. Some others arguments are available to configure the Elasticsearch index. For details of configuration, see the [ElasticsearchDependency section](#elasticsearchdependency).")  # fmt: off
    qdrant: QdrantDependency | None = Field(default=None, description="Pass all qdrant python SDK arguments, see https://python-client.qdrant.tech/qdrant_client.qdrant_client for more information.")  # fmt: off
    marker: MarkerDependency | None = Field(default=None, description="If provided, Marker API is used to parse pdf documents. Cannot be used with Albert dependency concurrently. Pass arguments to call Marker API in this section.")  # fmt: off
    postgres: PostgresDependency = Field(..., description="Pass all postgres python SDK arguments, see https://github.com/etalab-ia/opengatellm/blob/main/docs/dependencies/postgres.md for more information.")  # fmt: off
    redis: RedisDependency  = Field(..., description="Pass all `from_url()` method arguments of `redis.asyncio.connection.ConnectionPool` class, see https://redis.readthedocs.io/en/stable/connections.html#redis.asyncio.connection.ConnectionPool.from_url for more information.")  # fmt: off
    sentry: SentryDependency | None = Field(default=None, description="Pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information.")  # fmt: off
    proconnect: ProConnect | None = Field(default=None, description="ProConnect configuration for the API. See https://github.com/etalab-ia/albert-api/blob/main/docs/oauth2_encryption.md for more information.")  # fmt: off

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
        Check if only one dependency of each family is provided. For example, VectorStoreType can be Qdrant or Elasticsearch, but not both.

        The vector store dependency can be Qdrant or Elasticsearch, it is converted into a single attribute called "vector_store".
        The parser dependency can be Albert or Marker, it is converted into a single attribute called "parser".
        The web search engine dependency can be Brave or DuckDuckGo, it is converted into a single attribute called "web_search_engine".
        """

        def create_attribute(name: str, type: Enum, values: Any):
            candidates = [item for item in type if getattr(values, item.value) is not None]

            # Ensure only one dependency of this family is defined
            if len(candidates) > 1:
                raise ValueError(f"Only one {type.__name__} is allowed (provided: {", ".join(c.value for c in candidates)}).")

            # If no dependency is provided, set the attribute to None
            if len(candidates) == 0:
                setattr(values, name, None)
            else:
                chosen_enum = candidates[0]
                dep_obj = getattr(values, chosen_enum.value)

                # Add a `type` field on the dependency object to remember its family (string form)
                setattr(dep_obj, "type", chosen_enum)

                # Expose the dependency under the generic name (vector_store, parser, ...)
                setattr(values, name, dep_obj)

                # Clean up specific attributes
                for item in type:
                    if item != chosen_enum and hasattr(values, item.value):
                        delattr(values, item.value)

            return values

        self = create_attribute(name="web_search_engine", type=WebSearchEngineType, values=self)
        self = create_attribute(name="parser", type=ParserType, values=self)
        self = create_attribute(name="vector_store", type=VectorStoreType, values=self)

        return self


# settings -------------------------------------------------------------------------------------------------------------------------------------------

Routers = {str(router).upper(): str(router) for router in sorted(ROUTERS)}
Routers = Enum("Routers", Routers, type=str)


class LimitingStrategy(str, Enum):
    MOVING_WINDOW = "moving_window"
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"


class Tokenizer(str, Enum):
    TIKTOKEN_GPT2 = "tiktoken_gpt2"
    TIKTOKEN_R50K_BASE = "tiktoken_r50k_base"
    TIKTOKEN_P50K_BASE = "tiktoken_p50k_base"
    TIKTOKEN_P50K_EDIT = "tiktoken_p50k_edit"
    TIKTOKEN_CL100K_BASE = "tiktoken_cl100k_base"
    TIKTOKEN_O200K_BASE = "tiktoken_o200k_base"


@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#settings")
class Settings(ConfigBaseModel):
    # general
    disabled_routers: list[Routers] = Field(default_factory=list, description="Disabled routers to limits services of the API.", examples=[["embeddings"]])  # fmt: off
    hidden_routers: list[Routers] = Field(default_factory=list, description="Routers are enabled but hidden in the swagger and the documentation of the API.", examples=[["admin"]])  # fmt: off
    app_title: str | None = Field(default=DEFAULT_APP_NAME, description="Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API"])  # fmt: off

    # routing
    routing_max_retries: int = Field(default=3, ge=1, description="Maximum number of retries for routing tasks.")  # fmt: off
    routing_retry_countdown: int = Field(default=3, ge=1, description="Number of seconds before retrying a failed routing task.")  # fmt: off
    routing_max_priority: int = Field(default=4, ge=0, le=10, description="Maximum allowed priority in routing tasks.")  # fmt: off

    # usage tokenizer
    usage_tokenizer: Tokenizer = Field(default=Tokenizer.TIKTOKEN_GPT2, description="Tokenizer used to compute usage of the API.")  # fmt: off

    # logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Logging level of the API.")  # fmt: off
    log_format: str | None = Field(default="[%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s", description="Logging format of the API.")  # fmt: off

    # swagger
    swagger_summary: str | None = Field(default="OpenGateLLM connect to your models. You can configuration this swagger UI in the configuration file, like hide routes or change the title.", description="Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["My API description."])  # fmt: off
    swagger_version: str | None = Field(default="latest", description="Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["2.5.0"])  # fmt: off
    swagger_description: str | None = Field(default="[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)", description="Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.", examples=["[See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md)"])  # fmt: off
    swagger_contact: dict | None = Field(default=None, description="Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_license_info: dict | None = Field(default={"name": "MIT Licence", "identifier": "MIT", "url": "https://raw.githubusercontent.com/etalab-ia/opengatellm/refs/heads/main/LICENSE"}, description="Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_terms_of_service: str | None = Field(default=None, description="A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL.", examples=["https://example.com/terms-of-service"])  # fmt: off
    swagger_openapi_tags: list[dict[str, Any]] = Field(default_factory=list, description="OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_openapi_url: str | None = Field(default="/openapi.json", pattern=r"^/", description="OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_docs_url: str | None = Field(default="/docs", pattern=r"^/", description="Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off
    swagger_redoc_url: str | None = Field(default="/redoc", pattern=r"^/", description="Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information.")  # fmt: off

    # auth
    auth_master_key: constr(strip_whitespace=True, min_length=1) = Field(default="changeme", description="Master key for the API. It should be a random string with at least 32 characters. This key has all permissions and cannot be modified or deleted. This key is used to create the first role and the first user. This key is also used to encrypt user tokens, watch out if you modify the master key, you'll need to update all user API keys.")  # fmt: off
    auth_key_max_expiration_days: int | None = Field(default=None, ge=1, description="Maximum number of days for a new API key to be valid.")  # fmt: off
    auth_playground_session_duration: int = Field(default=3600, ge=1, description="Duration of the playground postgres_session in seconds.")  # fmt: off

    # rate_limiting
    rate_limiting_strategy: LimitingStrategy = Field(default=LimitingStrategy.FIXED_WINDOW, description="Rate limiting strategy for the API.")  # fmt: off

    # monitoring
    monitoring_postgres_enabled: bool = Field(default=True, description="If true, the log usage will be written in the PostgreSQL database.")  # fmt: off
    monitoring_prometheus_enabled: bool = Field(default=True, description="If true, Prometheus metrics will be exposed in the `/metrics` endpoint.")  # fmt: off

    # vector store
    vector_store_model: str | None = Field(default=None, description="Model used to vectorize the text in the vector store database. Is required if a vector store dependency is provided (Elasticsearch or Qdrant). This model must be defined in the `models` section and have type `text-embeddings-inference`.")  # fmt: off

    # search - web
    search_web_query_model: str | None = Field(default=None, description="Model used to query the web in the web search. Is required if a web search dependency is provided (Brave or DuckDuckGo). This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`.")  # fmt: off
    search_web_limited_domains: list[str] = Field(default_factory=list, description="Limited domains for the web search. If provided, the web search will be limited to these domains.")  # fmt: off
    search_web_user_agent: str | None = Field(default=None, description="User agent to scrape the web. If provided, the web search will use this user agent.")  # fmt: off

    # postgres_session
    session_secret_key: str | None = Field(default=None, description='Secret key for postgres_session middleware. If not provided, the master key will be used.', examples=["knBnU1foGtBEwnOGTOmszldbSwSYLTcE6bdibC8bPGM"])  # fmt: off

    front_url: str = Field(default="http://localhost:8501", description="Front-end URL for the application.")

    @model_validator(mode="after")
    def validate_model(self) -> Any:
        if self.session_secret_key is None:
            logging.warning("Session secret key not provided, using master key.")  # fmt: off
            self.session_secret_key = self.auth_master_key

        if len(self.auth_master_key) < 32:
            logging.warning("Auth master key is too short for production, it should be at least 32 characters.")  # fmt: off

        if any(router in self.hidden_routers for router in [ROUTER__ADMIN, ROUTER__AUTH]):
            logging.warning("Admin router should be hidden in production.")  # fmt: off

        if ROUTER__AUTH not in self.hidden_routers:
            logging.warning("Auth router should be hidden in production.")  # fmt: off

        return self


# load config ----------------------------------------------------------------------------------------------------------------------------------------
@custom_validation_error(url="https://docs.opengatellm.org/docs/getting-started/configuration#all-configuration")
class ConfigFile(ConfigBaseModel):
    models: list[Model] = Field(min_length=1, description="Models used by the API. At least one model must be defined.")  # fmt: off
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

        # check for duplicated name in models and aliases
        duplicated_models = [model for model in models["all"] if models["all"].count(model) > 1]
        if duplicated_models:
            raise ValueError(f"Duplicated model or alias names found: {", ".join(set(duplicated_models))}")

        # check for interdependencies
        if self.dependencies.vector_store:
            assert self.settings.vector_store_model, "Vector store model must be defined in settings section."
            assert self.settings.vector_store_model in models["all"], "Vector store model must be defined in models section."
            assert self.settings.vector_store_model in models[ModelType.TEXT_EMBEDDINGS_INFERENCE.value], f"The vector store model must have type {ModelType.TEXT_EMBEDDINGS_INFERENCE}."  # fmt: off

        if self.dependencies.web_search_engine:
            assert self.settings.search_web_query_model, "Web search query model must be defined in settings section."
            assert self.settings.search_web_query_model in models["all"], "Web search query model must be defined in models section."
            assert self.settings.search_web_query_model in models[ModelType.IMAGE_TEXT_TO_TEXT.value] + models[ModelType.TEXT_GENERATION.value], f"Web search query model must be defined in models section with type {ModelType.TEXT_GENERATION} or {ModelType.IMAGE_TEXT_TO_TEXT}."  # fmt: off

        return self


class Configuration(BaseSettings):
    model_config = ConfigDict(extra="allow")

    # config
    config_file: str = "config.yml"

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
