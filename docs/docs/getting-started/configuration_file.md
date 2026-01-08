# Configuration

OpenGateLLM requires configuring a configuration file. This defines models, dependencies, and settings parameters. Playground and API need a configuration file (could be the same file), see [API configuration](#api-configuration) and [Playground configuration](#playground-configuration).

By default, the configuration file must be `./config.yml` file.

You can change the configuration file by setting the `CONFIG_FILE` environment variable.

The configuration file has 3 sections:

- `models`: models configuration.
- `dependencies`: dependencies configuration.
- `settings`: settings configuration.

## Secrets

You can pass environment variables in configuration file with pattern `${ENV_VARIABLE_NAME}`. All environment variables will be loaded in the configuration file.

**Example**

```yaml
models:
  [...]
  - name: my-language-model
    type: text-generation
    providers:
      - type: openai
        url: https://api.openai.com
        key: ${OPENAI_API_KEY}
        model_name: gpt-4o-mini
```

## Example

The following is an example of configuration file:

```yaml
# ----------------------------------- models ------------------------------------
models:
  - name: albert-testbed
    type: text-generation
    # aliases: ["model-alias"]
    # owned_by: Me
    # load_balancing_strategy: shuffle
    # cost_prompt_tokens: 0.10
    # cost_completion_tokens: 0.10
    providers:
      - type: vllm
        url: http://albert-testbed.etalab.gouv.fr:8000
        # key: sk-xxx
        model_name: "gemma3:1b"
        # timeout: 60
        # model_carbon_footprint_zone: FRA
        # model_carbon_footprint_total_params: 8
        # model_carbon_footprint_active_params: 8
  
# -------------------------------- dependencies ---------------------------------
dependencies:
  postgres: # required
    url: postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-changeme}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/postgres
    echo: False
    pool_size: 5
    connect_args:
      server_settings:
        statement_timeout: "120s"
      command_timeout: 60

  redis: # required
    url: redis://:${REDIS_PASSWORD:-changeme}@${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}

  # elasticsearch:
  #   number_of_shards: 1
  #   number_of_replicas: 0
  #   hosts: "http://localhost:9200"
  #   basic_auth:
  #     - "elastic"
  #     - ${ELASTIC_PASSWORD}

  # sentry:
  #   dsn: ${SENTRY_DSN}

# ---------------------------------- settings -----------------------------------
settings:
  # session_secret_key: ${SESSION_SECRET_KEY}
  # disabled_routers: ["admin", "audio"]
  # usage_tokenizer: tiktoken_gpt2
  # app_title: My OpenGateLLM API

  # log_level: INFO
  # log_format: [%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s

  # swagger_version: 1.0.0
  # swagger_contact_url: https://github.com/etalab-ia/OpenGateLLM
  # swagger_contact_email: john.doe@example.com
  # swagger_docs_url: /docs
  # swagger_redoc_url: /redoc

  auth_master_username: master
  auth_master_key: changeme
  # auth_max_token_expiration_days: 365

  # rate_limiting_strategy: fixed_window

  # monitoring_sentry_enabled: True
  # monitoring_postgres_enabled: True
  # monitoring_prometheus_enabled: True

  # vector_store_model: my-model

  # search_multi_agents_synthesis_model: my-model
  # search_multi_agents_reranker_model: my-model

  playground_opengatellm_url: ${OPENGATELLM_URL:-http://localhost:8000}
  # playground_default_model: my-model
  # playground_theme_has_background: True
  # playground_theme_accent_color: purple
  # playground_theme_appearance: dark
  # playground_theme_gray_color: gray
  # playground_theme_panel_background: solid
  # playground_theme_radius: medium
  # playground_theme_scaling: 100%

```

## API configuration
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| dependencies | object | Dependencies used by the API. For details of configuration, see the [Dependencies section](#dependencies). |  |  |  |  |
| models | array | Models used by the API. For details of configuration, see the [Model section](#model). |  |  |  |  |
| settings | object | General settings configuration fields. For details of configuration, see the [Settings section](#settings). |  |  |  |  |

<br></br>

### Settings
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| app_title | string | Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | OpenGateLLM |  | My API |
| auth_key_max_expiration_days | integer | Maximum number of days for a new API key to be valid. |  | None |  |  |
| auth_master_key | string | Master key for the API. It should be a random string with at least 32 characters. This key has all permissions and cannot be modified or deleted. This key is used to create the first role and the first user. This key is also used to encrypt user tokens, watch out if you modify the master key, you'll need to update all user API keys. |  | changeme |  |  |
| auth_playground_session_duration | integer | Duration of the playground postgres_session in seconds. |  | 3600 |  |  |
| disabled_routers | array | Disabled routers to limits services of the API. |  |  | • admin<br></br>• audio<br></br>• auth<br></br>• chat<br></br>• chunks<br></br>• collections<br></br>• documents<br></br>• embeddings<br></br>• ... | ['embeddings'] |
| front_url | string | Front-end URL for the application. |  | http://localhost:8501 |  |  |
| hidden_routers | array | Routers are enabled but hidden in the swagger and the documentation of the API. |  |  | • admin<br></br>• audio<br></br>• auth<br></br>• chat<br></br>• chunks<br></br>• collections<br></br>• documents<br></br>• embeddings<br></br>• ... | ['admin'] |
| log_format | string | Logging format of the API. |  | [%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s |  |  |
| log_level | string | Logging level of the API. |  | INFO | • DEBUG<br></br>• INFO<br></br>• WARNING<br></br>• ERROR<br></br>• CRITICAL |  |
| monitoring_postgres_enabled | boolean | If true, the log usage will be written in the PostgreSQL database. |  | True |  |  |
| monitoring_prometheus_enabled | boolean | If true, Prometheus metrics will be exposed in the `/metrics` endpoint. |  | True |  |  |
| rate_limiting_strategy | string | Rate limiting strategy for the API. |  | fixed_window | • moving_window<br></br>• fixed_window<br></br>• sliding_window |  |
| routing_max_priority | integer | Maximum allowed priority in routing tasks. |  | 4 |  |  |
| routing_max_retries | integer | Maximum number of retries for routing tasks. |  | 3 |  |  |
| routing_retry_countdown | integer | Number of seconds before retrying a failed routing task. |  | 3 |  |  |
| session_secret_key | string | Secret key for postgres_session middleware. If not provided, the master key will be used. |  | None |  | knBnU1foGtBEwnOGTOmszldbSwSYLTcE6bdibC8bPGM |
| swagger_contact | object | Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | None |  |  |
| swagger_description | string | Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | [See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md) |  | [See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md) |
| swagger_docs_url | string | Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | /docs |  |  |
| swagger_license_info | object | Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | `{'name': 'MIT Licence', 'identifier': 'MIT', 'url': 'https://raw.githubusercontent.com/etalab-ia/opengatellm/refs/heads/main/LICENSE'}` |  |  |
| swagger_openapi_tags | array | OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  |  |  |  |
| swagger_openapi_url | string | OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | /openapi.json |  |  |
| swagger_redoc_url | string | Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | /redoc |  |  |
| swagger_summary | string | Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | OpenGateLLM connect to your models. You can configuration this swagger UI in the configuration file, like hide routes or change the title. |  | My API description. |
| swagger_terms_of_service | string | A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL. |  | None |  | https://example.com/terms-of-service |
| swagger_version | string | Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | latest |  | 2.5.0 |
| usage_tokenizer | string | Tokenizer used to compute usage of the API. |  | tiktoken_gpt2 | • tiktoken_gpt2<br></br>• tiktoken_r50k_base<br></br>• tiktoken_p50k_base<br></br>• tiktoken_p50k_edit<br></br>• tiktoken_cl100k_base<br></br>• tiktoken_o200k_base |  |
| vector_store_model | string | Model used to vectorize the text in the vector store database. Is required if a vector store dependency is provided (Elasticsearch or Qdrant). This model must be defined in the `models` section and have type `text-embeddings-inference`. |  | None |  |  |

<br></br>

### Model
In the models section, you define a list of models. Each model is a set of API providers for that model. Users will access the models specified in
this section using their *name*. Load balancing is performed between the different providers of the requested model. All providers in a model must
serve the same type of model (text-generation or text-embeddings-inference, etc.). We recommend that all providers of a model serve exactly the same
model, otherwise users may receive responses of varying quality. For embedding models, the API verifies that all providers output vectors of the
same dimension. You can define the load balancing strategy between the model's providers. By default, it is random.

For more information to configure model providers, see the [ModelProvider section](#modelprovider).
<br></br>

| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| aliases | array | Aliases of the model. It will be used to identify the model by users. |  |  |  | ['model-alias', 'model-alias-2'] |
| cost_completion_tokens | number | Model costs completion tokens for user budget computation. The cost is by 1M tokens. Set to `0.0` to disable budget computation for this model. |  | 0.0 |  | 0.1 |
| cost_prompt_tokens | number | Model costs prompt tokens for user budget computation. The cost is by 1M tokens. |  | 0.0 |  | 0.1 |
| load_balancing_strategy | string | Routing strategy for load balancing between providers of the model. |  | shuffle | • shuffle<br></br>• least_busy | least_busy |
| name | string | Unique name exposed to clients when selecting the model. |  |  |  | gpt-4o |
| providers | array | API providers of the model. If there are multiple providers, the model will be load balanced between them according to the routing strategy. The different models have to the same type. For details of configuration, see the [ModelProvider section](#modelprovider). |  |  |  |  |
| type | string | Type of the model. It will be used to identify the model type. |  |  | • automatic-speech-recognition<br></br>• image-text-to-text<br></br>• image-to-text<br></br>• text-embeddings-inference<br></br>• text-generation<br></br>• text-classification | text-generation |

<br></br>

#### ModelProvider
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| key | string | Model provider API key. |  | None |  | sk-1234567890 |
| model_carbon_footprint_active_params | integer | Active params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai |  | 0 |  | 8 |
| model_carbon_footprint_total_params | integer | Total params of the model in billions of parameters for carbon footprint computation. For more information, see https://ecologits.ai |  | 0 |  | 8 |
| model_carbon_footprint_zone | string | Model hosting zone using ISO 3166-1 alpha-3 code format (e.g., `WOR` for World, `FRA` for France, `USA` for United States). This determines the electricity mix used for carbon intensity calculations. For more information, see https://ecologits.ai |  | WOR | • ABW<br></br>• AFG<br></br>• AGO<br></br>• AIA<br></br>• ALA<br></br>• ALB<br></br>• AND<br></br>• ARE<br></br>• ... | WOR |
| model_name | string | Model name from the model provider. |  |  |  | gpt-4o |
| qos_limit | number | The value to use for the quality of service. Depends of the metric, the value can be a percentile, a threshold, etc. |  | None |  | 0.5 |
| qos_metric | string | The metric to use for the quality of service. If not provided, no QoS policy is applied. |  | None | • ttft<br></br>• latency<br></br>• inflight<br></br>• performance | inflight |
| timeout | integer | Timeout for the model provider requests, after user receive an 500 error (model is too busy). |  | 300 |  | 10 |
| type | string | Model provider type. |  |  | • albert<br></br>• openai<br></br>• mistral<br></br>• tei<br></br>• vllm | openai |
| url | string | Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI). |  | None |  | https://api.openai.com |

<br></br>

### Dependencies
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| albert | object | If provided, Albert API is used to parse pdf documents. Cannot be used with Marker dependency concurrently. Pass arguments to call Albert API in this section. For details of configuration, see the [AlbertDependency section](#albertdependency). |  | None |  |  |
| celery | object | If provided, Celery is used to run tasks asynchronously with queues. Pass arguments to call Celery in this section. For details of configuration, see the [CeleryDependency section](#celerydependency). |  | None |  |  |
| elasticsearch | object | Pass all elastic python SDK arguments, see https://elasticsearch-py.readthedocs.io/en/v9.0.2/api/elasticsearch.html#elasticsearch.Elasticsearch for more information. Some others arguments are available to configure the Elasticsearch index. For details of configuration, see the [ElasticsearchDependency section](#elasticsearchdependency). For details of configuration, see the [ElasticsearchDependency section](#elasticsearchdependency). |  | None |  |  |
| marker | object | If provided, Marker API is used to parse pdf documents. Cannot be used with Albert dependency concurrently. Pass arguments to call Marker API in this section. For details of configuration, see the [MarkerDependency section](#markerdependency). |  | None |  |  |
| postgres | object | Pass all postgres python SDK arguments, see https://github.com/etalab-ia/opengatellm/blob/main/docs/dependencies/postgres.md for more information. For details of configuration, see the [PostgresDependency section](#postgresdependency). |  |  |  |  |
| proconnect | object | ProConnect configuration for the API. See https://github.com/etalab-ia/albert-api/blob/main/docs/oauth2_encryption.md for more information. For details of configuration, see the [ProConnect section](#proconnect). |  | None |  |  |
| qdrant | object | Pass all qdrant python SDK arguments, see https://python-client.qdrant.tech/qdrant_client.qdrant_client for more information. For details of configuration, see the [QdrantDependency section](#qdrantdependency). |  | None |  |  |
| redis | object | Pass all `from_url()` method arguments of `redis.asyncio.connection.ConnectionPool` class, see https://redis.readthedocs.io/en/stable/connections.html#redis.asyncio.connection.ConnectionPool.from_url for more information. For details of configuration, see the [RedisDependency section](#redisdependency). |  |  |  |  |
| sentry | object | Pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information. For details of configuration, see the [SentryDependency section](#sentrydependency). |  | None |  |  |

<br></br>

#### SentryDependency

<br></br>

#### RedisDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| url | string | Redis connection url. |  |  |  | redis://:changeme@localhost:6379 |

<br></br>

#### QdrantDependency

<br></br>

#### ProConnect
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| allowed_domains | string | Comma-separated list of domains allowed to sign in via ProConnect (e.g. 'gouv.fr,example.com'). Only fronted on the specified domains will be allowed to authenticate using proconnect. |  | localhost,gouv.fr |  |  |
| client_id | string | Client identifier provided by ProConnect when you register your application in their dashboard. This value is public (it's fine to embed in clients) but must match the value configured in ProConnect. |  |  |  |  |
| client_secret | string | Client secret provided by ProConnect at application registration. This value must be kept confidential — it's used by the server to authenticate with ProConnect during token exchange (do not expose it to browsers or mobile apps). |  |  |  |  |
| default_role | string | Role automatically assigned to users created via ProConnect login on first sign-in. Set this to the role name you want new ProConnect users to receive (must exist in your roles configuration). |  | Freemium |  |  |
| redirect_uri | string | Redirect URI where users are sent after successful ProConnect authentication. This URI must exactly match one of the redirect URIs configured in OpenGateLLM settings. It must be an HTTPS endpoint in production and is used to receive the authorization tokens from ProConnect. |  | https://albert.api.etalab.gouv.fr/v1/auth/callback |  |  |
| scope | string | Space-separated OAuth2/OpenID Connect scopes requested from ProConnect (for example: 'openid email given_name'). Scopes determine the information returned about the authenticated user; reduce scopes to the minimum necessary for privacy. |  | openid email given_name usual_name siret organizational_unit belonging_population chorusdt |  |  |
| server_metadata_url | string | OpenID Connect discovery endpoint for ProConnect (server metadata). The SDK/flow uses this to discover authorization, token, and JWKS endpoints. Change to the production discovery URL when switching from sandbox to production. |  | https://identite-sandbox.proconnect.gouv.fr/.well-known/openid-configuration |  |  |

<br></br>

#### PostgresDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| url | string | PostgreSQL connection url. |  |  |  | postgresql://postgres:changeme@localhost:5432/postgres |

<br></br>

#### MarkerDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | Marker API request headers. |  |  |  | `{'Authorization': 'Bearer my-api-key'}` |
| timeout | integer | Timeout for the Marker API requests. |  | 300 |  | 10 |
| url | string | Marker API url. |  |  |  |  |

<br></br>

#### ElasticsearchDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| number_of_replicas | integer | Number of replicas for the Elasticsearch index. |  | 1 |  | 1 |
| number_of_shards | integer | Number of shards for the Elasticsearch index. |  | 1 |  | 1 |

<br></br>

#### CeleryDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| broker_url | string | Celery broker url like Redis (redis://) or RabbitMQ (amqp://). If not provided, use redis dependency as broker. |  | None |  |  |
| enable_utc | boolean | Enable UTC. |  | True |  | True |
| result_backend | string | Celery result backend url. If not provided, use redis dependency as result backend. |  | None |  |  |
| timezone | string | Timezone. |  | UTC |  | UTC |

<br></br>

#### AlbertDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | Albert API request headers. |  |  |  | `{'Authorization': 'Bearer my-api-key'}` |
| timeout | integer | Timeout for the Albert API requests. |  | 300 |  | 10 |
| url | string | Albert API url. |  | https://albert.api.etalab.gouv.fr |  |  |

<br></br>

## Playground configuration
The following parameters allow you to configure the Playground application. The configuration file can be shared with the API, as the sections are
identical and compatible. Some parameters are common to both the API and the Playground (for example, `app_title`).

For Plagroud deployment, some environment variables are required to be set, like Reflex backend URL. See
[Environment variables](../getting-started/environment_variables.md#playground) for more information.
<br></br>

| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| dependencies | object | Dependencies used by the playground. For details of configuration, see the [Dependencies section](#dependencies). |  |  |  |  |
| settings | object | General settings configuration fields. Some fields are common to the API and the playground. For details of configuration, see the [Settings section](#settings). |  |  |  |  |

<br></br>

### Settings
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| app_title | string | The title of the application. |  | OpenGateLLM |  |  |
| auth_key_max_expiration_days | integer | Maximum number of days for a token to be valid. |  | None |  |  |
| documentation_url | string | Documentation URL. If not provided, deactivated documentation link in the navigation bar. |  | https://docs.opengatellm.org/docs |  |  |
| playground_default_model | string | The first model selected in chat page. |  | None |  |  |
| playground_opengatellm_timeout | integer | The timeout in seconds for the OpenGateLLM API. |  | 60 |  |  |
| playground_opengatellm_url | string | The URL of the OpenGateLLM API. |  | http://localhost:8000 |  |  |
| playground_theme_accent_color | string | The primary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors. |  | purple |  |  |
| playground_theme_appearance | string | The appearance of the theme. |  | light |  |  |
| playground_theme_gray_color | string | The secondary color used for default buttons, typography, backgrounds, etc. See available colors at https://www.radix-ui.com/colors. |  | gray |  |  |
| playground_theme_has_background | boolean | Whether the theme has a background. |  | True |  |  |
| playground_theme_panel_background | string | Whether panel backgrounds are translucent: 'solid' | 'translucent'. |  | solid |  |  |
| playground_theme_radius | string | The radius of the theme. Can be 'small', 'medium', or 'large'. |  | medium |  |  |
| playground_theme_scaling | string | The scaling of the theme. |  | 100% |  |  |
| reference_url | string | Reference URL. If not provided, deactivated reference link in the navigation bar. |  | http://localhost:8000/redoc |  |  |
| routing_max_priority | integer | Maximum allowed priority in routing tasks. |  | 10 |  |  |
| swagger_url | string | Swagger URL. If not provided, deactivated swagger link in the navigation bar. |  | http://localhost:8000/docs |  |  |

<br></br>

### Dependencies
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| redis | object | Set the Redis connection url to use as stage manager. See https://reflex.dev/docs/api-reference/config/ for more information. For details of configuration, see the [RedisDependency section](#redisdependency). |  | None |  |  |

<br></br>

#### RedisDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| url | string | Redis connection url. |  |  |  | redis://:changeme@localhost:6379 |

<br></br>

