# Commit and hooks

## Commit name convention

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```

## Linter

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the `pyproject.toml` file.

Please install the pre-commit hooks to run the linter at each commit:

  ```bash
  pre-commit install
  ```

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