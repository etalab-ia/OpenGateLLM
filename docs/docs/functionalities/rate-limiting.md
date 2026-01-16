# Rate Limiting

OpenGateLLM provides a robust rate limiting system to control the traffic and usage of your LLM routers. This ensures fair usage and prevents abuse of the provided resources.

## Concepts

The rate limiting system is built around **role limits** defined for specific **routers**. Each user has a role, and each role can have customized limits for different models/routers.

The usage counters and quotas are tracked per user (not shared across users with the same role), so each user's consumption is measured and enforced individually to ensure fair usage and accurate throttling.

## Limit Types

There are four types of limits that can be enforced for each role/router pair:

- **RPM (Requests Per Minute)**: Limits the number of API requests a user can make in a minute.
- **RPD (Requests Per Day)**: Limits the number of API requests a user can make in a day.
- **TPM (Tokens Per Minute)**: Limits the number of input tokens (prompt tokens) a user can process in a minute.
- **TPD (Tokens Per Day)**: Limits the number of input tokens (prompt tokens) a user can process in a day.

## Strategies

OpenGateLLM supports multiple rate-limiting algorithms (strategies), which determine how the usage window is calculated. You can configure this via the `LimitingStrategy` setting in your configuration.

- **Fixed Window** (`fixed_window`): Counts requests in fixed time windows (e.g., 12:00-12:01, 12:01-12:02). This is the most performance-efficient but can allow bursts at window boundaries.
- **Moving Window** (`moving_window`): A more precise method that ensures the limit is respected in any time window of the specified duration.
- **Sliding Window** (`sliding_window`): A hybrid approach, typically providing a balance between accuracy and performance.

### Implementation Details

The rate limiter is implemented using the [limits](https://limits.readthedocs.io/en/stable/) Python library backed by [Redis](https://redis.io/).

Here is an example of how to reference the `LimitingStrategy` in your configuration:

```py
# Example configuration snippet usage references
from api.schemas.core.configuration import LimitingStrategy

# ...
```

## Request Flow & Order of Checks

When a user makes a request, the system checks limits in the following order:

1.  **Access Check**: Verifies if the user is allowed to access the requested router at all. If no limits are defined for this router, the user is denied access (`404 Model Not Found`).
2.  **Permission Check**: If any of the user's limits for the router are set to `0`, the request is rejected immediately (`403 Insufficient Permissions`).
3.  **RPM Check**: Increments and checks the Requests Per Minute counter.
4.  **RPD Check**: Increments and checks the Requests Per Day counter.
5.  **Token Checks**: If the request involves tokens (e.g., chat completions), it proceeds to check:
    *   **TPM Check**: Increments usage by the number of prompt tokens.
    *   **TPD Check**: Increments usage by the number of prompt tokens.

If any of these limits are exceeded, a `429 Too Many Requests` error is returned with details on which limit was breached and the remaining quota.

Note: Users with ID `0` (Administrators) bypass all rate limits and access checks.
