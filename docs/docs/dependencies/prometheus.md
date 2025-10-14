# Prometheus

OpenGateLLM can expose metrics in Prometheus format for monitoring and observability. This allows you to track API performance, usage patterns, and system health in real-time.

:::info
Prometheus is an **optional dependency**. If not configured, OpenGateLLM will continue to work but without metrics exposure.
:::

## Overview

When Prometheus monitoring is enabled, OpenGateLLM exposes metrics at the `/metrics` endpoint in Prometheus format. These metrics can be scraped by a Prometheus server for visualization in tools like Grafana.

## Setup Prometheus

### Prerequisites

- A Prometheus server to scrape metrics (optional but recommended)
- Grafana or similar visualization tool (optional)

### Configuration

:::info
For more information about the configuration file, see [Configuration](../getting-started/configuration.md) documentation.
:::

Enable Prometheus metrics in the `settings` section of your `config.yml`:

```yaml
settings:
    [...]
    monitoring_prometheus_enabled: true
```

By default, Prometheus monitoring is enabled. Set it to `false` to disable the `/metrics` endpoint.

## Access Prometheus Metrics

Once enabled, you can access the metrics at:

```
http://localhost:8000/metrics
```

This endpoint returns metrics in Prometheus text-based exposition format, which can be scraped by Prometheus server.
