# Development environment

## Prerequisites

- Python 3.12+
- Docker and Docker Compose

## Packages installation

1. Create a Python virtual environment (recommended)

1. Install the dependencies with the following command:

  ```bash
  pip install ".[api,playground,dev,test]"
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

4. Check the [configuration documentation](./docs/configuration.md) to configure your configuration file.

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

3. Launch the Playground:
  ```bash
  streamlit run playground/main.py
  ```

## Linter

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](./pyproject.toml)* file. See [Linter installation section](#linter-installation) to install the linter and run it at each commit.

To run the linter manually:

```bash
make lint
```

To setup ruff in VSCode or Cursor, you can add the following configuration to your editor (edit project root path):

```json
{
  "[python]": {
        "editor.formatOnType": true,
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": "explicit",
            "source.organizeImports": "always"
        },
    "ruff.configuration": "<absolute project root path >/pyproject.toml",
    "ruff.format.preview": true,
    "ruff.codeAction.fixViolation": {"enable": false},
    "ruff.organizeImports": true,
    "ruff.fixAll": true,
    "ruff.trace.server": "verbose",
    "ruff.logLevel": "debug",
    "ruff.nativeServer": "on",
  }
}
```

## Commit

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```

## Tests

To run the tests:

```bash
make test
```

## Modifications to SQL database structure

### Modifications to the [`api/sql/models.py`](./api/sql/models.py) file

If you have modified the API database tables in the [models.py](./api/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c api/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c api/alembic.ini upgrade head
```

### Modifications to the [`playground/sql/models.py`](./playground/sql/models.py) file

If you have modified the playground database tables in the [models.py](./playground/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c playground/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c playground/alembic.ini upgrade head
```

