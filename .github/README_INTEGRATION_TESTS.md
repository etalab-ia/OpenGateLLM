# Integration tests

> [!WARNING]
> **For internal team use only.**

The configuration file is in the `api/tests/integ/config.test.yml` file.

## Run all integration tests (make command)

### Prerequisites

- Docker
- Docker Compose
- Virtual environment with packages installed (see [CONTRIBUTING.md](../CONTRIBUTING.md)) (optional)

### Start services and run tests

To start services and run tests, you can use the following command:

```bash
make test-integ 
```

### Start services for integration tests

To start services for integration tests without running tests, you can use the following command:

```bash
make test-integ [action=up|down|run|all] [execute=local|docker]
```

> [!NOTE]
> The `action` parameter is optional and defaults to `all`. This parameter is used to specify the action to perform:
> - `up`: Setup environment without running tests
> - `run`: Run tests without setup environment
> - `all`: Setup environment and run tests
> - `down`: Stop services

> [!NOTE]
> To run the integration tests locally, you need to set the following environment variables in the `.github/.env.ci` file:
>
> - `POSTGRES_HOST` must be set to `localhost`
> - `REDIS_HOST` must be set to `localhost`
> - `ELASTICSEARCH_HOST` must be set to `localhost`
> - `BRAVE_API_KEY` must be set to your Brave API key
> - `ALBERT_API_KEY` must be set to your Albert API key

### Example

* Run tests in local environment:

    ```bash
    make test-integ action=run execute=local
    ```

* Setup environment before running tests:

    ```bash
    make test-integ action=up execute=local
    ```

    Then run tests:

    ```bash
    make test-integ action=run execute=local
    ```

## Run a specific test

To execute a specific test, you can use the following command:

```bash
CONFIG_FILE=api/tests/integ/config.test.yml PYTHONPATH=. pytest api/tests/integ/<path_to_test_file>::<TestClass>::<test_name> --config-file=pyproject.toml

# Example
CONFIG_FILE=api/tests/integ/config.test.yml PYTHONPATH=. pytest api/tests/integ/test_admin/test_admin_providers.py::TestAdminProviders::test_create_provider_with_text_generation_model --config-file=pyproject.toml
```

To run a group of tests, you can use the following command:

```bash
CONFIG_FILE=api/tests/integ/config.test.yml PYTHONPATH=. pytest api/tests/integ/<path_to_test_file> --config-file=pyproject.toml

# Example
CONFIG_FILE=api/tests/integ/config.test.yml PYTHONPATH=. pytest api/tests/integ/test_admin/test_admin_providers.py --config-file=pyproject.toml
```

## Run with VSCode

Create a `.vscode/settings.json` file with the following content:

```json
{
    "python.testing.pytestArgs": [
        "api", "-v", "-s", "--config-file=pyproject.toml"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/.github/.env.ci"
}
```
