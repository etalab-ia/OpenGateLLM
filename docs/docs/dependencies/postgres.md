# Postgres

OpenGateLLM uses PostgreSQL as its primary relational database to manage application resources and track API usage. 

:::info
PostgreSQL is a **required dependency** for OpenGateLLM to function.
:::

## Overview

PostgreSQL stores and manages:
- **Identity & Access Management (IAM)**: Users, roles, permissions, tokens, and organizations
- **Usage Logs**: API call tracking with metrics (tokens, costs, duration, carbon footprint)
- **Document Management**: Collections and documents for RAG functionality
- **Model Registry**: Model configurations, providers, and aliases

The database includes the following main tables:

### Identity & Access Management

- **`user`**: User accounts with authentication information
- **`role`**: User roles for permission management
- **`permission`**: Fine-grained permissions assigned to roles
- **`token`**: API tokens for authentication
- **`organization`**: Organizations for grouping users

### Usage Tracking

- **`usage`**: Comprehensive API usage logs including:
  - Request metadata (endpoint, method, model)
  - Token consumption (prompt, completion, total)
  - Performance metrics (duration, time to first token)
  - Cost tracking
  - Environmental impact (kWh, CO₂ emissions)

### Document Management

- **`collection`**: Document collections for RAG
- **`document`**: Documents stored in collections

### Model Registry

- **`model`**: Model routers and configurations
- **`model_client`**: Model provider clients
- **`model_alias`**: Model aliases for routing

## Setup PostgreSQL

### Prerequisites

PostgreSQL 16 or higher is recommended.

### Configuration

#### Docker Compose

Add a `postgres` container in the `services` section of your `compose.yml` file:

```yaml
services:
  [...]
  postgres:
    image: postgres:16.5
    restart: always
    user: postgres
    environment:
      - "POSTGRES_USER=${POSTGRES_USER:-postgres}"
      - "POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}"
      - "POSTGRES_DB=postgres"
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    volumes:
      - postgres:/var/lib/postgresql/data
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready", "-U", "postgres" ]
      interval: 4s
      timeout: 10s
      retries: 5
      start_period: 60s

volumes:
  postgres:
```

#### Configuration File

:::info
For more information about the configuration file, see [Configuration](../getting-started/configuration.md) documentation.
:::

1. Add PostgreSQL configuration in the `dependencies` section of your `config.yml`. Example:

        ```yaml
        dependencies:
            [...]
            postgres:
                url: postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-changeme}@${POSTGRES_HOST:-localhost}:${POSTGRES_PORT:-5432}/postgres
                echo: false
                pool_size: 5
                connect_args:
                server_settings:
                    statement_timeout: "120s"
                command_timeout: 60
        ```

        The PostgreSQL dependency accepts all parameters from the [SQLAlchemy AsyncEngine](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine). Only `url` parameter is required.

        :::warning
        The connection URL must use the `postgresql+asyncpg://` driver. If you provide a standard `postgresql://` URL, it will be automatically converted to use asyncpg.
        :::

    2. For usage monitoring, set `monitoring_postgres_enabled` to `true` in settings (enabled by default).

        ```yaml
        settings:
            [...]
            monitoring_postgres_enabled: true
        ```

        All requests to the API are logged in the `usage` table. For more information about usage tracking, see [Usage monitoring documentation](../functionalities/usage.md).

## Database Migrations

OpenGateLLM uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. The schema is automatically initialized and updated when the API starts by [`startup_api.sh` script](https://github.com/etalab-ia/OpenGateLLM/blob/main/scripts/startup_api.sh).

For contributing to the database schema, you can follow the instructions in [SQL contributions documentation](../contributing/sql.md).

### Data Retention

For production deployments, consider implementing a data retention policy for the `usage` table to manage database size.
