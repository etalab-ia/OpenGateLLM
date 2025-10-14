# Sentry

OpenGateLLM supports [Sentry](https://sentry.io/welcome/) for error tracking and performance monitoring. Sentry helps you identify, diagnose, and fix errors in real-time.

:::info
Sentry is an **optional dependency** for OpenGateLLM. The application works without it, but enabling Sentry provides valuable insights into errors and performance issues.
:::

## Setup Sentry

### Prerequisites

1. A Sentry account (cloud or self-hosted)
2. A Sentry DSN (Data Source Name) for your project

You can create a free account at [sentry.io](https://sentry.io/welcome/) or [self-host Sentry](https://develop.sentry.dev/self-hosted/).

### Configuration

#### Configuration File

:::info
For more information about the configuration file, see [Configuration](../getting-started/configuration.md) documentation.
:::

Add Sentry configuration in the `dependencies` section of your `config.yml`. Example:

```yaml
dependencies:
  [...]
  sentry:
    dsn: ${SENTRY_DSN}
    environment: ${SENTRY_ENVIRONMENT:-production}
    traces_sample_rate: 1.0
    profiles_sample_rate: 1.0
    enable_tracing: true
```

The Sentry dependency accepts all parameters from the [Sentry Python SDK](https://docs.sentry.io/platforms/python/configuration/options/). Only the `dsn` parameter is typically required.
