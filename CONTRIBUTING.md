# Contributing

The contributings guides is available in *Contributing* section in [documentation](https://docs.opengatellm.org/docs/):
- [Development environment](https://docs.opengatellm.org/docs/contributing/development-environment)
- [Commit and hooks](https://docs.opengatellm.org/docs/contributing/commit)
- [SQL](https://docs.opengatellm.org/docs/contributing/sql)
- [Documentation](https://docs.opengatellm.org/docs/contributing/documentation)


## Run tests
### Unit tests
```bash
make test-unit
```

### Integration tests

```bash
make test-integ
```

To run a specific test, you can use the following command:
```bash
make test-integ test_chunk.py::TestChunks::test_get_chunks
```

### VScode configuration

Create a `.vscode/settings.json` file with the following content:

```json
{
    "python.terminal.activateEnvironment": true,
    "python.testing.pytestArgs": [
        "api", "-s", "--config-file=pyproject.toml"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.envFile": "${workspaceFolder}/.github/.env.ci"
}
```