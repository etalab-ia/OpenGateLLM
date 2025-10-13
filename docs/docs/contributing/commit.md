# Commit and hooks

## Commit name convention

Please respect the following convention for your commits:

```
[doc|feat|fix](theme) commit object (in english)

# example
feat(collections): collection name retriever
```

### Linter installation

The project linter is [Ruff](https://beta.ruff.rs/docs/configuration/). The specific project formatting rules are in the *[pyproject.toml](./pyproject.toml)* file.

Please install the pre-commit hooks:

  ```bash
  pre-commit install
  ```

Ruff will run automatically at each commit.

To setup ruff in VSCode or Cursor, you can add the following configuration to your editor:
```json
{
  "ruff.lint.enabled": true,
  "ruff.lint.fix": true
}
```
