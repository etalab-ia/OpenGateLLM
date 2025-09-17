# Commit to OpenGateLLM
## Commit name convention

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```

## Pre-commit hooks
You can install the pre-commit hooks (linter):
  ```bash
  pre-commit install
  ```
The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](https://github.com/etalab-ia/OpenGateLLM/blob/main/pyproject.toml)* file.

Ruff will run automatically at each commit.

You can run the linter manually:

```bash
make lint
```


