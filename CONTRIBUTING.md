# Contributing

To contribute to the project, please follow the instructions below.

## Development environment

1. Create a *config.yml* file based on the example configuration file *[config.example.yml](./config.example.yml)* with your models.

```bash
cp config.example.yml config.yml && export CONFIG_FILE=./config.yml
cp .env.example .env && export APP_ENV_FILE=.env
```

Check the [configuration documentation](./docs/configuration.md) to configure your configuration file.

    > **❗️Note**<br>
    > The configuration file for running tests is [config.test.yml](./.github/config.test.yml). You can use it as inspiration to configure your own configuration file.

2. Set up dependencies

    ```bash
    docker compose --env-file .env up postgres redis elasticsearch secretiveshell --detach 

    pip install ".[app,ui,dev,test]" # install the dependencies

    alembic -c app/alembic.ini upgrade head # create the API tables
    alembic -c ui/alembic.ini upgrade head # create the Playground tables
    ```

3. Launch the API

    ```bash
    uvicorn app.main:app --port 8080 --log-level debug --reload
    ```

4. Launch the playground

    In another terminal, launch the playground with the following command:

    ```bash
    streamlit run ui/main.py --server.port 8501 --theme.base light
    ```

    To connect to the playground for the first time, use the login *master* and password *changeme* (defined in the configuration file).

## Modifications to SQL database structure

### Modifications to the [`app/sql/models.py`](./app/sql/models.py) file

If you have modified the API database tables in the [models.py](./app/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c app/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c app/alembic.ini upgrade head
```

### Modifications to the [`ui/sql/models.py`](./ui/sql/models.py) file

If you have modified the UI database tables in the [models.py](./ui/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c ui/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c ui/alembic.ini upgrade head
```

## Tests

### In Docker environment

```bash
make env-ci-up
docker exec albert-ci-api-1 pytest app/tests --cov=./app --cov-report=xml
```

> **❗️Note**<br>
> It will create a .github/.env.ci file.
> The configuration file for running tests is [config.test.yml](app/tests/integ/config.test.yml). You can modify it to run the tests on your machine.
> You need set `$BRAVE_API_KEY` and `$ALBERT_API_KEY` environment variables in `.github/.env.ci` to run the tests.
### Outside Docker environment

1. Create a `.env.test` file and run the databases services:

    ```bash 
    cp .env.example .env.test
    make env-test-services-up
    ```
   
2. Install the python packages:

   ```bash
   make install
   ```

3. To run the unit and integration tests together:

    ```bash
    make test-all
    ```
   
4. To run the unit tests:

    ```bash
    make test-unit
    ```
 
5. To run the integration tests:

    ```bash
    make test-integ
    ```


6. To update the snapshots, run the following command:

    ```bash
    CONFIG_FILE=./.github/config.test.yml PYTHONPATH=. pytest --config-file=pyproject.toml --snapshot-update
    ```

If you want integration tests to use mocked responses, you need to enable VCR by adding to your .env file:

```
VCR_ENABLED=true
```

When you run the integration tests, it will store responses from databases, apis into the app/test/integ/cassettes folder and use them when you rerun the tests

## Notebooks

It is important to keep the notebooks in the docs/tutorials folder up to date, to show quick examples of API usage.

To launch the notebooks locally:

```bash
pip install ".[dev]"
jupyter notebook docs/tutorials/
```

## Linter

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](./pyproject.toml)* file.

Please install the pre-commit hooks:

```bash
pip install ".[dev]"
pre-commit install
```

Ruff will run automatically at each commit.

## Commit

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```


And modify the `models` section in the `config.yml` file:

The API keys can be defined directement in the `config.yml` file or in a `.env` file

```bash
cp .env.test.example .env.test

echo 'ALBERT_API_KEY=my_albert_api_key' >> .env.test
echo 'OPENAI_API_KEY=my_openai_api_key' >> .env.test
```

Finally, run the application:
```bash
make docker-compose-albert-api-up
```

To stop the application, run:
```bash
make docker-compose-albert-api-down
```


## Running locally

### Prerequisites
- Python 3.8+
- Docker and Docker Compose

### Installation

#### 1. Installing dependencies

```bash
make install
```

#### 2. Configuration

Albert-API supports OpenAI and Albert-API models, defined in the `config.yml` file :
```bash
cp config.example.yml config.yml
```

And modify the `models` section in the `config.yml` file:

```yaml
models:
  - id: albert-large
    type: text-generation
    owned_by: test
    aliases: ["mistralai/Mistral-Small-3.1-24B-Instruct-2503"]
    clients:
      - model: mistralai/Mistral-Small-3.1-24B-Instruct-2503
        type: albert
        args:
          api_url: ${ALBERT_API_URL:-https://albert.api.etalab.gouv.fr}
          api_key: ${ALBERT_API_KEY}
          timeout: 120
  - id: my-language-model
    type: text-generation
    clients:
      - model: gpt-3.5-turbo
        type: openai
        params:
          total: 70
          active: 70
          zone: WOR
        args:
          api_url: https://api.openai.com
          api_key: ${OPENAI_API_KEY}
          timeout: 60
```
The API keys can be defined directement in the `config.yml` file or in a `.env` file

```bash
cp .env.example .env

echo 'ALBERT_API_KEY=my_albert_api_key' >> .env
echo 'OPENAI_API_KEY=my_openai_api_key' >> .env
```

### Running

#### Option 1: Full launch with Docker

```bash
# Start all services (API, playground and external services)
make docker-compose-albert-api-up
# Stop all services
make docker-compose-albert-api-down
```

#### Option 2: Local development

```bash
# 1. Start only external services (Redis, Qdrant, PostgreSQL, MCP Bridge)
make docker-compose-services-up

# 2. Launch the API (in one terminal)
make run-api

# 3. Launch the user interface (in another terminal)
make run-ui
```
