# Redis

OpenGateLLM uses Redis as an in-memory data store for rate limiting and performance metrics. Redis provides high-performance, real-time data access for managing API quotas and monitoring model performance.

:::info
Redis is a **required dependency** for OpenGateLLM to function.
:::

## Overview

Redis handles two critical functions in OpenGateLLM:

- **Rate Limiting**: Tracks and enforces API usage limits (requests per minute/day, tokens per minute/day) for each user and model
- **Performance Metrics**: Stores time-series data for model performance monitoring (latency, time to first token)

### Rate Limiting

The rate limiter uses Redis to store counters for:
- **RPM (Requests Per Minute)**: Number of API requests per minute per user and model
- **RPD (Requests Per Day)**: Number of API requests per day per user and model  
- **TPM (Tokens Per Minute)**: Number of tokens consumed per minute per user and model
- **TPD (Tokens Per Day)**: Number of tokens consumed per day per user and model

OpenGateLLM supports three rate limiting strategies (configurable in settings):
- **Fixed Window**: Limits are enforced in fixed time windows
- **Sliding Window**: Limits are enforced using a sliding time window for smoother distribution
- **Moving Window**: Limits are enforced with a moving average approach

For more information about rate limiting, see [Rate Limiting documentation](../functionalities/iam/roles-permissions-rate-limitings.md).

### Performance Metrics

Redis time-series module stores performance metrics for each model provider:
- **Latency**: Total request duration in milliseconds
- **Time to First Token**: Time until the first token is generated (for streaming responses)

These metrics are used for monitoring and can be exposed via Prometheus when enabled.

## Setup Redis

### Prerequisites

Redis Stack Server 7.2+ is required (includes the time-series module).

### Configuration

#### Docker Compose

Add a `redis` container in the `services` section of your `compose.yml` file:

```yaml
services:
  [...]
  redis:
    image: redis/redis-stack-server:7.2.0-v11
    restart: always
    environment:
      REDIS_ARGS: "--dir /data --requirepass ${REDIS_PASSWORD:-changeme} --user ${REDIS_USER:-redis} on >password ~* allcommands --save 60 1 --appendonly yes"
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis:/data
    healthcheck:
      test: [ "CMD", "redis-cli", "--raw", "incr", "ping" ]
      interval: 4s
      timeout: 10s
      retries: 5

volumes:
  redis:
```

:::warning
**Redis Stack Server** is required (not standard Redis) because OpenGateLLM uses the [RedisTimeSeries module](https://redis.io/docs/data-types/timeseries/) for performance metrics.
:::

#### Configuration File

:::info
For more information about the configuration file, see [Configuration](../getting-started/configuration.md) documentation.
:::

1. Add Redis configuration in the `dependencies` section of your `config.yml`. Example:

        ```yaml
        dependencies:
            [...]
            redis:
                host: ${REDIS_HOST:-localhost}
                port: ${REDIS_PORT:-6379}
                password: ${REDIS_PASSWORD:-changeme}
        ```

        The Redis dependency accepts all parameters from the [coredis ConnectionPool](https://coredis.readthedocs.io/en/stable/handbook/connections.html#connection-pools). The `host`, `port`, and `password` parameters are most commonly used.

2. Configure rate limiting strategy in the `settings` section of your `config.yml` (default is `fixed_window`):

        ```yaml
        settings:
            [...]
            rate_limiting_strategy: fixed_window
        ```

        For more information about rate limiting, see [Rate Limiting documentation](../functionalities/iam/roles-permissions-rate-limitings.md).

3. Configure metrics retention in the `settings` section of your `config.yml` (default is 40 seconds):

        ```yaml
        settings:
            [...]
            metrics_retention_ms: 40000  # in milliseconds
        ```

        Theses metrics are stored in Redis time-series module to determine request prioritisation. For more information about request prioritisation, see [request prioritisation documentation](../models/request_prioritisation.md).
