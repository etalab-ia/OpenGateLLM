```mermaid
flowchart LR
  classDef boundary fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray:5 5,color:#424242;
  classDef api fill:#e3f2fd,stroke:#1e88e5,color:#0d47a1;
  classDef broker fill:#fff3e0,stroke:#ef6c00,color:#e65100;
  classDef worker fill:#e8f5e9,stroke:#43a047,color:#1b5e20;
  classDef redis fill:#ffebee,stroke:#e53935,color:#b71c1c;
  classDef client fill:#ede7f6,stroke:#5e35b1,color:#311b92;
  classDef provider fill:#fff9c4,stroke:#fbc02d,color:#f57f17;

  Client((Client)):::client

  subgraph API[API Container]
    class API boundary
    FastAPI[FastAPI<br/>Gunicorn/Uvicorn]:::api
  end

  subgraph MQ[RabbitMQ Broker]
    class MQ boundary
    Q[(Model Queues<br/>router.X, router.Y...)]:::broker
  end

  subgraph CW[Celery Routing Worker]
    class CW boundary
    WR((routing.apply<br/>Pick provider_id)):::worker
  end

  subgraph R[Redis]
    class R boundary
    REDIS[(Redis<br/>LB metrics + QoS + Task result + Performance metrics)]:::redis
  end

  subgraph PROVIDER[Target LLM Servers]
    class PROVIDER boundary
    S1((Provider 1)):::provider
    S2((Provider 2)):::provider
    S3((Provider N)):::provider
  end

  Client -->|POST /v1/chat/completions| FastAPI
  FastAPI -->|INCR inflight & log metrics| REDIS

  FastAPI -->|apply_async to queue| Q
  Q --> WR
  WR -->|read LB/QoS metrics| REDIS
  WR -->|store routing result| REDIS
  FastAPI -->|poll AsyncResult| REDIS
  FastAPI -->|forward request to selected provider| PROVIDER
  PROVIDER -- Completion response --> FastAPI
  FastAPI -->|DECR inflight & log latency| REDIS
  FastAPI -- Response --> Client

  ```

```mermaid
sequenceDiagram
  participant Client
  participant API as FastAPI
  participant REDIS as Redis (metrics + backend)
  participant RMQ as RabbitMQ (router.X)
  participant CW as Celery Worker (routing.apply)
  participant Provider as LLM Provider

  Client->>API: POST /v1/chat/completions
  API->>REDIS: INCR inflight::<model_id>

  API->>RMQ: apply_routing.apply_async(queue="router.X")
  API->>REDIS: Poll AsyncResult (until ready)

  RMQ-->>CW: Deliver routing task
  CW->>REDIS: Read LB & QoS metrics
  CW->>CW: Choose provider_id
  CW->>REDIS: Store routing result
  API->>REDIS: Retrieve result (provider_id)

  API->>Provider: Forward request using httpx
  Provider-->>API: Completion response
  API->>REDIS: DECR inflight::<model_id>
  API->>REDIS: Log latency metric::<model_id>

  API-->>Client: JSON completion response

```
