```mermaid
flowchart LR
  classDef boundary fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray: 5 5,color:#424242;
  classDef proc fill:#e3f2fd,stroke:#1e88e5,stroke-width:1px,color:#0d47a1;
  classDef broker fill:#fff3e0,stroke:#ef6c00,color:#e65100;
  classDef cworker fill:#e8f5e9,stroke:#43a047,color:#1b5e20;
  classDef client fill:#ede7f6,stroke:#5e35b1,color:#311b92;

  Client((HTTP Client)):::client

  subgraph API[Host/Container: API service]
    class API boundary
    M(Gunicorn Master):::proc
    subgraph GW[Gunicorn worker processes N]
      class GW boundary
      W1[UvicornWorker #1<br/>FastAPI app]:::proc
      W2[UvicornWorker #2<br/>FastAPI app]:::proc
      Wn[UvicornWorker #N<br/>FastAPI app]:::proc
    end
    M --> W1
    M --> W2
    M --> Wn
  end

  Client -->|HTTP| M

  subgraph MQB[Broker]
    class MQB boundary
    MQ[(RabbitMQ)]:::broker
  end

  subgraph CWG[Celery worker nodes]
    class CWG boundary
    C1[[celery worker Q1]]:::cworker
    C2[[celery worker Q2,Q3,Q4]]:::cworker
    Cn[[celery worker QN]]:::cworker
  end

  %% FastAPI publishes tasks
  W1 -- "celery.apply_async" --> MQ
  W2 -- "celery.apply_async" --> MQ
  Wn -- "celery.apply_async" --> MQ

  %% Celery workers consume tasks
  MQ --> C1
  MQ --> C2
  MQ --> Cn

  %% Optional: result backend (could be Redis/DB)
  RB[Result backend<br/>Redis]:::broker
  C1 --> RB
  C2 --> RB
  Cn --> RB

  %% FastAPI polls for results if you're using 202+poll pattern
  W1 -. fetch status/result .-> RB
  W2 -. fetch status/result .-> RB
  Wn -. fetch status/result .-> RB
  ```

  sequenceDiagram
  participant Client
  participant Master as Gunicorn master
  participant API as FastAPI worker (Uvicorn)
  participant RMQ as RabbitMQ
  participant CW as Celery worker
  participant RB as Result backend (optional)

```mermaid
sequenceDiagram
  participant Client
  participant Master as Gunicorn master
  participant API as FastAPI worker (Uvicorn)
  participant RMQ as RabbitMQ
  participant CW as Celery worker
  participant RB as Result backend (optional)

  Client->>Master: HTTP POST /do-thing
  Master->>API: Dispatch request to a worker
  API->>RMQ: Publish task (apply_async)
  RMQ-->>CW: Deliver task from queue
  CW->>CW: Execute task
  alt Store results
    CW-->>RB: Save result/status
  end
  API-->>Client: 202 Accepted + task_id
  loop Polling
    Client->>API: GET /tasks/{task_id}
    API->>RB: Read status/result
    RB-->>API: State/result
    API-->>Client: 200 Done | 202 Pending | 4xx/5xx
  end
```