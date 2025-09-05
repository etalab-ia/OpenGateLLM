# All settings
Refer to the [configuration example file](../../../config.example.yml) for an example of configuration.
<br>

| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| dependencies | object | Dependencies used by the API. For details of configuration, see the [Dependencies section](#dependencies). |  |  |  |  |
| models | array | Models used by the API. At least one model must be defined. For details of configuration, see the [Model section](#model). |  |  |  |  |
| settings | object | Settings used by the API. For details of configuration, see the [Settings section](#settings). |  |  |  |  |

<br>

## Settings
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| auth_master_key | string | Master key for the API. It should be a random string with at least 32 characters. This key has all permissions and cannot be modified or deleted. This key is used to create the first role and the first user. This key is also used to encrypt user tokens, watch out if you modify the master key, you'll need to update all user API keys. |  | changeme |  |  |
| auth_max_token_expiration_days | integer | Maximum number of days for a token to be valid. |  | None |  |  |
| disabled_routers | array | Disabled routers to limits services of the API. |  |  | • admin.organizations<br/>• admin.roles<br/>• admin.tokens<br/>• admin.users<br/>• agents<br/>• audio<br/>• auth<br/>• chat<br/>• ... | ['agents', 'embeddings'] |
| front_url | string | Front-end URL for the application. |  | http://localhost:8501 |  |  |
| hidden_routers | array | Routers are enabled but hidden in the swagger and the documentation of the API. |  |  | • admin.organizations<br/>• admin.roles<br/>• admin.tokens<br/>• admin.users<br/>• agents<br/>• audio<br/>• auth<br/>• chat<br/>• ... | ['admin'] |
| log_format | string | Logging format of the API. |  | [%(asctime)s][%(process)d:%(name)s][%(levelname)s] %(client_ip)s - %(message)s |  |  |
| log_level | string | Logging level of the API. |  | INFO | • DEBUG<br/>• INFO<br/>• WARNING<br/>• ERROR<br/>• CRITICAL |  |
| mcp_max_iterations | integer | Maximum number of iterations for MCP agents in `/v1/agents/completions` endpoint. |  | 2 |  |  |
| metrics_retention_ms | integer | Retention time for metrics in milliseconds. |  | 40000 |  |  |
| monitoring_postgres_enabled | boolean | If true, the log usage will be written in the PostgreSQL database. |  | True |  |  |
| monitoring_prometheus_enabled | boolean | If true, Prometheus metrics will be exposed in the `/metrics` endpoint. |  | True |  |  |
| rate_limiting_strategy | string | Rate limiting strategy for the API. |  | fixed_window | • moving_window<br/>• fixed_window<br/>• sliding_window |  |
| search_multi_agents_reranker_model | string | Model used to rerank the results of multi-agents search. If not provided, multi-agents search is disabled. This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`. |  | None |  |  |
| search_multi_agents_synthesis_model | string | Model used to synthesize the results of multi-agents search. If not provided, multi-agents search is disabled. This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`. |  | None |  |  |
| search_web_limited_domains | array | Limited domains for the web search. If provided, the web search will be limited to these domains. |  |  |  |  |
| search_web_query_model | string | Model used to query the web in the web search. Is required if a web search dependency is provided (Brave or DuckDuckGo). This model must be defined in the `models` section and have type `text-generation` or `image-text-to-text`. |  | None |  |  |
| search_web_user_agent | string | User agent to scrape the web. If provided, the web search will use this user agent. |  | None |  |  |
| session_secret_key | string | Secret key for session middleware. If not provided, the master key will be used. |  | None |  | knBnU1foGtBEwnOGTOmszldbSwSYLTcE6bdibC8bPGM |
| swagger_contact | object | Contact informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | None |  |  |
| swagger_description | string | Display description of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | [See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md) |  | [See documentation](https://github.com/etalab-ia/opengatellm/blob/main/README.md) |
| swagger_docs_url | string | Docs URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | /docs |  |  |
| swagger_license_info | object | Licence informations of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | {'name': 'MIT Licence', 'identifier': 'MIT', 'url': 'https://raw.githubusercontent.com/etalab-ia/opengatellm/refs/heads/main/LICENSE'} |  |  |
| swagger_openapi_tags | array | OpenAPI tags of the API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  |  |  |  |
| swagger_openapi_url | string | OpenAPI URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | /openapi.json |  |  |
| swagger_redoc_url | string | Redoc URL of swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | /redoc |  |  |
| swagger_summary | string | Display summary of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | Albert API connect to your models. You can configuration this swagger UI in the configuration file, like hide routes or change the title. |  | Albert API connect to your models. |
| swagger_terms_of_service | string | A URL to the Terms of Service for the API in swagger UI. If provided, this has to be a URL. |  | None |  | https://example.com/terms-of-service |
| swagger_title | string | Display title of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | Albert API |  | Albert API |
| swagger_version | string | Display version of your API in swagger UI, see https://fastapi.tiangolo.com/tutorial/metadata for more information. |  | latest |  | 2.5.0 |
| usage_tokenizer | string | Tokenizer used to compute usage of the API. |  | tiktoken_gpt2 | • tiktoken_gpt2<br/>• tiktoken_r50k_base<br/>• tiktoken_p50k_base<br/>• tiktoken_p50k_edit<br/>• tiktoken_cl100k_base<br/>• tiktoken_o200k_base |  |
| vector_store_model | string | Model used to vectorize the text in the vector store database. Is required if a vector store dependency is provided (Elasticsearch or Qdrant). This model must be defined in the `models` section and have type `text-embeddings-inference`. |  | None |  |  |

<br>

## Model
In the models section, you define a list of models. Each model is a set of API providers for that model. Users will access the models specified in
this section using their *name*. Load balancing is performed between the different providers of the requested model. All providers in a model must
serve the same type of model (text-generation or text-embeddings-inference, etc.). We recommend that all providers of a model serve exactly the same
model, otherwise users may receive responses of varying quality. For embedding models, the API verifies that all providers output vectors of the
same dimension. You can define the load balancing strategy between the model's providers. By default, it is random.

For more information to configure model providers, see the [ModelProvider section](#modelprovider).
<br>

| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| aliases | array | Aliases of the model. It will be used to identify the model by users. |  |  |  | ['model-alias', 'model-alias-2'] |
| created | integer | Time of creation, as Unix timestamp. |  | None |  |  |
| from_config | boolean | Whether this model was defined in configuration, meaning it should be checked against the database. |  | False |  |  |
| max_context_length | integer | Maximum amount of tokens a context could contains. Makes sure it is the same for all models. |  | None |  |  |
| owned_by | string | Owner of the model displayed in `/v1/models` endpoint. |  | Albert API |  | my-app |
| providers | array | API providers of the model. If there are multiple providers, the model will be load balanced between them according to the routing strategy. The different models have to the same type. For details of configuration, see the [ModelProvider section](#modelprovider). |  |  |  |  |
| routing_strategy | string | Routing strategy for load balancing between providers of the model. It will be used to identify the model type. |  | shuffle | • round_robin<br/>• shuffle | round_robin |
| type | string | Type of the model. It will be used to identify the model type. |  |  | • image-text-to-text<br/>• automatic-speech-recognition<br/>• text-embeddings-inference<br/>• text-generation<br/>• text-classification | text-generation |
| vector_size | integer | Dimension of the vectors, if the models are embeddings. Makes just it is the same for all models. |  | None |  |  |

<br>

### ModelProvider
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| key | string | Model provider API key. |  | None |  | sk-1234567890 |
| model_carbon_footprint_active_params | number | Active params of the model in billions of parameters for carbon footprint computation. If not provided, the total params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai |  | None |  | 8 |
| model_carbon_footprint_total_params | number | Total params of the model in billions of parameters for carbon footprint computation. If not provided, the active params will be used if provided, else carbon footprint will not be computed. For more information, see https://ecologits.ai |  | None |  | 8 |
| model_carbon_footprint_zone | string | Model hosting zone for carbon footprint computation (with ISO 3166-1 alpha-3 code format). For more information, see https://ecologits.ai |  | WOR | • ABW<br/>• AFG<br/>• AGO<br/>• AIA<br/>• ALA<br/>• ALB<br/>• AND<br/>• ARE<br/>• ... | WOR |
| model_cost_completion_tokens | number | Model costs completion tokens for user budget computation. The cost is by 1M tokens. |  | 0.0 |  | 0.1 |
| model_cost_prompt_tokens | number | Model costs prompt tokens for user budget computation. The cost is by 1M tokens. |  | 0.0 |  | 0.1 |
| model_name | string | Model name from the model provider. |  |  |  | gpt-4o |
| timeout | integer | Timeout for the model provider requests, after user receive an 500 error (model is too busy). |  | 300 |  | 10 |
| type | string | Model provider type. |  |  | • albert<br/>• openai<br/>• tei<br/>• vllm | openai |
| url | string | Model provider API url. The url must only contain the domain name (without `/v1` suffix for example). Depends of the model provider type, the url can be optional (Albert, OpenAI). |  | None |  | https://api.openai.com |

<br>

## Dependencies
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| albert | object | If provided, Albert API is used to parse pdf documents. Cannot be used with Marker dependency concurrently. Pass arguments to call Albert API in this section. For details of configuration, see the [AlbertDependency section](#albertdependency). |  | None |  |  |
| brave | object | If provided, Brave API is used to web search. Cannot be used with DuckDuckGo dependency concurrently. Pass arguments to call API in this section. All query parameters are supported, see https://api-dashboard.search.brave.com/app/documentation/web-search/query for more information. For details of configuration, see the [BraveDependency section](#bravedependency). |  | None |  |  |
| centralesupelec | object | Needed to pass tests where models are added For details of configuration, see the [CentraleSupelecDependency section](#centralesupelecdependency). |  | None |  |  |
| duckduckgo | object | If provided, DuckDuckGo API is used to web search. Cannot be used with Brave dependency concurrently. Pass arguments to call API in this section. All query parameters are supported, see https://www.searchapi.io/docs/duckduckgo-api for more information. For details of configuration, see the [DuckDuckGoDependency section](#duckduckgodependency). |  | None |  |  |
| elasticsearch | object | Pass all elastic python SDK arguments, see https://elasticsearch-py.readthedocs.io/en/v9.0.2/api/elasticsearch.html#elasticsearch.Elasticsearch for more information. For details of configuration, see the [ElasticsearchDependency section](#elasticsearchdependency). |  |  |  |  |
| marker | object | If provided, Marker API is used to parse pdf documents. Cannot be used with Albert dependency concurrently. Pass arguments to call Marker API in this section. For details of configuration, see the [MarkerDependency section](#markerdependency). |  | None |  |  |
| postgres | object | Pass all postgres python SDK arguments, see https://github.com/etalab-ia/opengatellm/blob/main/docs/dependencies/postgres.md for more information. For details of configuration, see the [PostgresDependency section](#postgresdependency). |  |  |  |  |
| proconnect | object | ProConnect configuration for the API. See https://github.com/etalab-ia/albert-api/blob/main/docs/oauth2_encryption.md for more information. For details of configuration, see the [ProConnect section](#proconnect). |  | None |  |  |
| qdrant | object | Pass all qdrant python SDK arguments, see https://python-client.qdrant.tech/qdrant_client.qdrant_client for more information. For details of configuration, see the [QdrantDependency section](#qdrantdependency). |  | None |  |  |
| redis | object | Pass all redis python SDK arguments, see https://redis.readthedocs.io/en/stable/connections.html for more information. For details of configuration, see the [RedisDependency section](#redisdependency). |  |  |  |  |
| secretiveshell | object | If provided, MCP agents can use tools from SecretiveShell MCP Bridge. Pass arguments to call Secretiveshell API in this section, see https://github.com/SecretiveShell/MCP-Bridge for more information. For details of configuration, see the [SecretiveshellDependency section](#secretiveshelldependency). |  | None |  |  |
| sentry | object | Pass all sentry python SDK arguments, see https://docs.sentry.io/platforms/python/configuration/options/ for more information. For details of configuration, see the [SentryDependency section](#sentrydependency). |  | None |  |  |

<br>

### SentryDependency

<br>

### SecretiveshellDependency
See https://github.com/SecretiveShell/MCP-Bridge for more information.
<br>

| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | Secretiveshell API request headers. |  |  |  |  |
| timeout | integer | Timeout for the Secretiveshell API requests. |  | 300 |  | 10 |
| url | string | Secretiveshell API url. |  |  |  |  |

<br>

### RedisDependency

<br>

### QdrantDependency

<br>

### ProConnect
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| allowed_domains | string | Comma-separated list of domains allowed to sign in via ProConnect (e.g. 'gouv.fr,example.com'). Only fronted on the specified domains will be allowed to authenticate using proconnect. |  | localhost,gouv.fr |  |  |
| client_id | string | Client identifier provided by ProConnect when you register your application in their dashboard. This value is public (it's fine to embed in clients) but must match the value configured in ProConnect. |  |  |  |  |
| client_secret | string | Client secret provided by ProConnect at application registration. This value must be kept confidential — it's used by the server to authenticate with ProConnect during token exchange (do not expose it to browsers or mobile apps). |  |  |  |  |
| default_role | string | Role automatically assigned to users created via ProConnect login on first sign-in. Set this to the role name you want new ProConnect users to receive (must exist in your roles configuration). |  | Freemium |  |  |
| redirect_uri | string | Redirect URI where users are sent after successful ProConnect authentication. This URI must exactly match one of the redirect URIs configured in OpenGateLLM settings. It must be an HTTPS endpoint in production and is used to receive the authorization tokens from ProConnect. |  | https://albert.api.etalab.gouv.fr/v1/auth/callback |  |  |
| scope | string | Space-separated OAuth2/OpenID Connect scopes requested from ProConnect (for example: 'openid email given_name'). Scopes determine the information returned about the authenticated user; reduce scopes to the minimum necessary for privacy. |  | openid email given_name usual_name siret organizational_unit belonging_population chorusdt |  |  |
| server_metadata_url | string | OpenID Connect discovery endpoint for ProConnect (server metadata). The SDK/flow uses this to discover authorization, token, and JWKS endpoints. Change to the production discovery URL when switching from sandbox to production. |  | https://identite-sandbox.proconnect.gouv.fr/.well-known/openid-configuration |  |  |

<br>

### PostgresDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| url | string | PostgreSQL connection url. |  |  |  |  |

<br>

### MarkerDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | Marker API request headers. |  |  |  | {'Authorization': 'Bearer my-api-key'} |
| timeout | integer | Timeout for the Marker API requests. |  | 300 |  | 10 |
| url | string | Marker API url. |  |  |  |  |

<br>

### ElasticsearchDependency

<br>

### DuckDuckGoDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | DuckDuckGo API request headers. | False |  |  | {} |
| timeout | integer | Timeout for the DuckDuckGo API requests. |  | 300 |  | 10 |
| url | string | DuckDuckGo API url. |  | https://api.duckduckgo.com/ |  |  |

<br>

### CentraleSupelecDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| token | string | Centrale Supélec token for testing dynamic models |  |  |  |  |

<br>

### BraveDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | Brave API request headers. | True |  |  | {'X-Subscription-Token': 'my-api-key'} |
| timeout | integer | Timeout for the Brave API requests. |  | 300 |  | 10 |
| url | string | Brave API url. |  | https://api.search.brave.com/res/v1/web/search |  |  |

<br>

### AlbertDependency
| Attribute | Type | Description | Required | Default | Values | Examples |
| --- | --- | --- | --- | --- | --- | --- |
| headers | object | Albert API request headers. |  |  |  | {'Authorization': 'Bearer my-api-key'} |
| timeout | integer | Timeout for the Albert API requests. |  | 300 |  | 10 |
| url | string | Albert API url. |  | https://albert.api.etalab.gouv.fr |  |  |

<br>

