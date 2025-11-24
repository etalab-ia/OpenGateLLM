# Development environment

## Prerequisites

- Python 3.12+
- Docker and Docker Compose

## Packages installation

1. Create a Python virtual environment (recommended)

1. Install the dependencies with the following command:

  ```bash
  pip install ".[api,worker,playground,dev,test]"
  ```

## Configuration

It is recommended to use a Python [virtualenv](https://docs.python.org/3/library/venv.html).

1. Create a *config.yml* file based on the example configuration file *[config.example.yml](./config.example.yml)*. 

  ```bash
  cp config.example.yml config.yml
  ```

2. Create a *env* file based on the example environment file *[env.example](./env.example)*

  ```bash
  cp .env.example .env
  ```

3. Comment host names variables like this (by default, they are set to `localhost` in compose.example.yml):

  ```bash
  # POSTGRES_HOST=postgres
  ```

4. Check the [configuration documentation](../getting-started/configuration.md) to configure your configuration file.

## Launch services

Start services locally with the following command:

```bash
make dev
```

:::tip
This command will start the API and the playground services and support the following options:
```bash
make dev [service=api|playground|both] [env=.env] [compose=compose.yml] # service=both by default
```
For more information, run `make help`.
:::


To run the services without make command, you can use the following commands:

1. Export the environment variables:
  ```bash
    export $(grep -v '^#' .env | xargs) 
  ```

2. Launch the API:
  ```bash
  uvicorn api.main:app --log-level debug --reload
  ```

  The API will be available at http://localhost:8000.

3. Launch the Playground:
  ```bash
  cd playground
  reflex run --env dev --loglevel debug
  ```

  The playground will be available at http://localhost:8501. 
