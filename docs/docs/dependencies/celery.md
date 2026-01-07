# Celery

OpenGateLLM uses **Celery** to perform asynchronous routing and load balancing when request queuing is enabled.  
Celery workers compute the optimal LLM provider using real-time metrics stored in Redis.

:::info
Celery is **optional**, but required when request queuing is enabled.
:::

## Overview

Celery provides asynchronous task execution, responsible primarily for:

- **Request Routing**  
  The API publishes a routing task to the Celery broker.  
  A worker:
  - reads LB/QoS metrics from Redis  
  - selects the best provider  
  - writes the provider_id result to Redis  

The API then reads that result and forwards the request to the chosen provider.

When queuing is enabled:

- **Broker**: RabbitMQ (recommended) or Redis  
- **Result Backend**: Redis (default)

### Routing Workflow (High-Level)

1. API receives request  
2. API increments inflight counters in Redis  
3. API submits routing task  
4. Celery worker consumes task  
5. Worker reads metrics from Redis  
6. Worker stores provider_id result in Redis  
7. API retrieves result  
8. API forwards the request to provider  
9. API decrements inflight counters and logs latency

---

## Celery Configuration

Defined under `dependencies.celery` in `config.yml`.

### Configuration Model

```python
class CeleryDependency(ConfigBaseModel):
    broker_url: constr(strip_whitespace=True, min_length=1) | None = Field(
        default=None,
        description="Celery broker url like Redis (redis://) or RabbitMQ (amqp://). If not provided, use redis dependency as broker."
    )
    result_backend: constr(strip_whitespace=True, min_length=1) | None = Field(
        default=None,
        description="Celery result backend url. If not provided, use redis dependency as result backend."
    )
    timezone: str = Field(default="UTC", description="Timezone.", examples=["UTC"])
    enable_utc: bool = Field(default=True, description="Enable UTC.", examples=[True])
```

### Example config.yml

```yaml
dependencies:
  redis:
    url: redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}

  celery:
    broker_url: amqp://guest:guest@rabbitmq:5672//
    result_backend: redis://:${REDIS_PASSWORD}@redis:6379/0
    timezone: UTC
    enable_utc: true
```


Default behavior:
- If `broker_url` is missing → Redis is used as broker
- If `result_backend` is missing → Redis is used as result backend

---

## Deployment With Docker Compose

### Worker Service Example

```yaml
services:
  worker:
    build:
      context: ..
      dockerfile: api/Dockerfile
      target: worker
      args:
        BUILD_TARGET: worker
    volumes:
      - "../${CONFIG_FILE}:/config.yml:ro"
    environment:
      - RABBITMQ_HOST=rabbitmq
      - REDIS_HOST=redis
      - CELERY_EXTRA_ARGS=${CELERY_EXTRA_ARGS:-}
    depends_on:
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
```

### Worker Startup Command (in Dockerfile)

```
CMD ["celery", "-A", "opengate.worker", "worker", "--loglevel=INFO"]
```

---

## Queues

Celery uses:

- **router.X** – queue used by the API  
- **routing.apply** – Celery task executed by workers  

Workers bind automatically on startup.

---

## Scaling Workers

```
docker compose up --scale worker=4 -d
```

Celery distributes routing tasks across all workers.

---

## Summary

Celery enables asynchronous routing in OpenGateLLM:

- Broker: RabbitMQ or Redis  
- Result Backend: Redis (default)  
- Workers compute provider selection using live metrics  
- Redis stores routing results for API polling  
