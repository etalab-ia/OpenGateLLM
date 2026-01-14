# Rate Limiting

OpenGateLLM provides a robust rate limiting system to control the traffic and usage of your LLM routers. This ensures fair usage and prevents abuse of the provided resources.

## Concepts

The rate limiting system is built around user limits for specific routers. Each user can have multiple limits defined for different routers.

### Limit Types

There are four types of limits that can be enforced:

- **RPM (Requests Per Minute)**: Limits the number of API requests a user can make in a minute.
- **RPD (Requests Per Day)**: Limits the number of API requests a user can make in a day.
- **TPM (Tokens Per Minute)**: Limits the number of input tokens (prompt tokens) a user can process in a minute.
- **TPD (Tokens Per Day)**: Limits the number of input tokens (prompt tokens) a user can process in a day.

### Strategies

The rate limiter supports different strategies for tracking usage. This depends on the `LimitingStrategy` configuration.

- **Fixed Window** (`fixed_window`): Counts requests in fixed time windows (e.g., 12:00-12:01, 12:01-12:02). This is the most performance-efficient but can allow bursts at window boundaries.
- **Moving Window** (`moving_window`): A more precise method that ensures the limit is respected in *any* time window of the specified duration.
- **Sliding Window** (`sliding_window`): A hybrid approach, typically providing a balance between accuracy and performance.

The underlying implementation uses the [limits](https://limits.readthedocs.io/en/stable/) python library and stores state in **Redis**.

## How it works

When a request is received:

1. **User Identification**: The system identifies the user making the request.
2. **Limit Retrieval**: It retrieves the limits associated with the role the user belongs to, for the specific router being accessed.
3. **Limit Checks**: The system checks the limits in the following order:
    1. **RPM**: Checks if the requests per minute limit is exceeded.
    2. **RPD**: Checks if the requests per day limit is exceeded.
    3. **TPM**: Checks if the tokens per minute limit is exceeded (requires token count).
    4. **TPD**: Checks if the tokens per day limit is exceeded (requires token count).

If any of these limits are exceeded, a `429 Too Many Requests` error is returned (specifically a `RateLimitExceeded` exception).

:::info
Admin users (ID 0) are exempt from all rate limits.
:::

## Configuration

The rate limiting strategy is configured in your application settings.

Limiting is backed by **Redis**, ensuring it works correctly even with multiple API replicas (distributed rate limiting) and fast performance.

```python
# Example configuration snippet usage references
from api.schemas.core.configuration import LimitingStrategy

# ...
```
