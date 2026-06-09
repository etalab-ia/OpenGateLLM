# ADR - 2026-05-28 - Refactoring model forwarding 

* **Status:**
* **Date:** 2026-05-28
* **Authors:** Development Team
* **Decision Outcome:**

---

### Context

The previous model forwarding path concentrated several responsibilities in infrastructure classes. The gateway selected providers, forwarded HTTP requests, adapted provider payloads, computed usage, updated metrics and relied on request context side effects. This made the forwarding flow hard to test in isolation and forced business rules to be spread across infrastructure objects.

The refactoring moves orchestration back to the use case layer. The use case now describes the complete business flow: load the user and router, validate access and router type, select a provider, build the endpoint adapter, compute prompt tokens, apply rate limits, forward the request, format the response, compute usage and log metrics. Infrastructure implementations remain replaceable details behind domain contracts.

This branch applies the pattern first to the rerank endpoint. The same structure is intended to be reused by the other model forwarding endpoints.


### Legend

```mermaid
flowchart LR

a([function]) --> b[class] --> c@{ shape: procs, label: Multiple class}

linkStyle 0 stroke:transparent;
linkStyle 1 stroke:transparent;
```

### Previous architecture
```mermaid
---
config:
  layout: elk
---
flowchart LR

subgraph UL[**Use cases layer**]
    use_case[Model forwarding use case]
end

subgraph DL[**Domain layer**]

    subgraph Router
        router_repository[RouterRepository]
    end
    subgraph Provider
        provider_repository[ProviderRepository]
        provider_metrics_logger[ProviderMetricsLogger]
    end
    subgraph User
        user_with_role_query[UserWithRoleQuery]
    end
end

subgraph IL[**Infrastructure layer**]
    subgraph Model
        model_provider_gateway[ModelProviderGateway]
        model_http_client@{ shape: procs, label: ModelHttpClient}
        model_usage_computer[ModelUsageComputer]
        model_tokenizer_computer[ModelTokenizerComputer]
        endpoint_adapter@{ shape: procs, label: EndpointAdapter}
    end
    subgraph Fastapi
        request_manager[RequestContextManager]
    end

    subgraph Redis
        redis_provider_metrics_logger[RedisProviderMetricsLogger]
    end
    subgraph Postgres
        postgres_router_repository[PostgresRouterRepository]
        postgres_provider_repository[PostgresProviderRepository]
        postgres_user_with_role_query[PostgresUserWithRoleQuery]
    end
end

use_case --> model_provider_gateway
use_case --> router_repository
use_case --> provider_repository
use_case --> user_with_role_query

router_repository --> postgres_router_repository
provider_repository --> postgres_provider_repository
user_with_role_query --> postgres_user_with_role_query

model_provider_gateway --VLLM, Mistral, TEI...--> model_http_client

model_provider_gateway --> request_manager
model_http_client --> model_usage_computer
model_usage_computer --> model_tokenizer_computer
model_http_client --Chat completions, OCR, Rerank...--> endpoint_adapter
provider_metrics_logger --> redis_provider_metrics_logger
model_http_client --> provider_metrics_logger

style UL fill:#FCF0FC
style DL fill:#F0FCF6
style IL fill:#FCF8F0
```

### New architecture

The new architecture follows the principles of clean architecture: the model forwarding use case contains the business logic and directly orchestrates the domain abstractions. Dependencies remain simple to call and understand: objects do not call each other implicitly, they expose focused contracts that are explicitly composed by the use case.


#### Major changes

* **Use case as orchestrator:** `CreateRerankUseCase` owns the forwarding sequence and calls each dependency explicitly. This keeps the business flow readable in one place and avoids hidden calls between provider, router, metrics and HTTP objects.
* **Domain contracts for forwarding:** provider client, provider load balancer, router rate limiter, model tokenizer and environmental impact computer are exposed as domain abstractions. The use case depends on these contracts, not on Redis, HTTP, Ecologit or Tiktoken directly.
* **HTTP client simplified:** `HttpProviderClient` only sends an already formatted request to the selected provider and returns the raw provider response or a model error. It no longer owns endpoint selection, usage computation, metrics or rate limiting.
* **Endpoint adapters extracted:** provider-specific adapters convert OpenGate requests and responses to each provider format. `build_adapter` selects the right adapter from the source endpoint and provider type, while common usage computation stays in the base adapter.
* **Redis responsibilities isolated:** Redis implementations handle provider load balancing, provider metrics and router rate limits behind dedicated contracts. The use case decides when those operations happen.
* **Usage and impacts made explicit:** prompt tokens are computed before rate limiting, response usage is computed after provider response formatting, and environmental impacts are delegated to the Ecologit implementation through a domain contract.
* **FastAPI endpoint thinned:** the HTTP endpoint builds the command, calls the use case and maps domain errors to HTTP exceptions. It no longer contains forwarding logic.
* **Tests follow boundaries:** unit tests cover the use case and adapters, while integration tests cover Redis, HTTP client, Ecologit, Tiktoken, Postgres repositories and the rerank endpoint.

```mermaid
---
config:
  layout: elk
---
flowchart LR

subgraph UL[**Use cases layer**]
    use_case[Model forwarding use case]
end

subgraph DL[**Domain layer**]
    subgraph Router
        router_repository[RouterRepository]
        router_rate_limiter[RouterRateLimiter]
    end
    subgraph Provider
        provider_repository[ProviderRepository]
        provider_gateway[ProviderGateway]
        provider_load_balancer[ProviderLoadBalancer]
        provider_client[ProviderClient]
        provider_metrics_logger[ProviderMetricsLogger]
    end
    subgraph Model
        model_environmental_impacts_computer[ModelEnvironmentalImpactsComputer]
        model_tokenizer[ModelTokenizer]
    end
    subgraph User
        user_with_role_query[UserWithRoleQuery]
    end
end

subgraph IL[**Infrastructure layer**]
    subgraph Fastapi
        request_manager[RequestContextManager]
    end
    subgraph HTTP
        http_provider_client[HttpProviderClient]
        build_adapter([build_adapter])
        endpoint_adapter@{ shape: procs, label: EndpointAdapter}
    end


    subgraph Ecologit
        ecologit_model_environmental_impacts_computer[EcologitModelEnvironmentalImpactsComputer]
    end

    subgraph Tiktoken
        tiktoken_model_tokenizer[TiktokenModelTokenizer]
    end

    subgraph Redis
        redis_provider_metrics_logger[RedisProviderMetricsLogger]
        redis_provider_load_balancer[RedisProviderLoadBalancer]
        redis_router_rate_limiter[RedisRouterRateLimiter]
    end
    subgraph Postgres
        postgres_router_repository[PostgresRouterRepository]
        postgres_provider_repository[PostgresProviderRepository]
        postgres_user_with_role_query[PostgresUserWithRoleQuery]
    end
end

use_case --> router_repository
use_case --> router_rate_limiter
use_case --> provider_repository
use_case --> provider_gateway
use_case --> provider_load_balancer
use_case --> provider_client
use_case --> provider_metrics_logger
use_case --> model_environmental_impacts_computer
use_case --> model_tokenizer
use_case --> user_with_role_query

use_case --> request_manager
use_case --> build_adapter


provider_client --> http_provider_client
build_adapter --VLLM, Mistral, TEI...<br>Chat completions, OCR, Rerank...--> endpoint_adapter
model_environmental_impacts_computer --> ecologit_model_environmental_impacts_computer
model_tokenizer --> tiktoken_model_tokenizer
provider_metrics_logger --> redis_provider_metrics_logger
provider_load_balancer --> redis_provider_load_balancer
router_rate_limiter --> redis_router_rate_limiter
router_repository --> postgres_router_repository
provider_repository --> postgres_provider_repository
user_with_role_query --> postgres_user_with_role_query

style UL fill:#FCF0FC
style DL fill:#F0FCF6
style IL fill:#FCF8F0
```

