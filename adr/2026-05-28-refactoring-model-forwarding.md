# ADR - 2026-05-28 - Refactoring model forwarding 

* **Status:**
* **Date:** 2026-05-28
* **Authors:** Development Team
* **Decision Outcome:**

---

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

