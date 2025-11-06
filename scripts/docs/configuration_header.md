# Configuration

OpenGateLLM requires configuring a configuration file. This defines models, dependencies, and settings parameters. Playground and API need a configuration file (could be the same file), see [API configuration](#api-configuration) and [Playground configuration](#playground-configuration).

By default, the configuration file must be `./config.yml` file.

You can change the configuration file by setting the `CONFIG_FILE` environment variable.

The configuration file has 3 sections:

- `models`: models configuration.
- `dependencies`: dependencies configuration.
- `settings`: settings configuration.

## Secrets

You can pass environment variables in configuration file with pattern `${ENV_VARIABLE_NAME}`. All environment variables will be loaded in the configuration file.

**Example**

```yaml
models:
  [...]
  - name: my-language-model
    type: text-generation
    providers:
      - type: openai
        url: https://api.openai.com
        key: ${OPENAI_API_KEY}
        model_name: gpt-4o-mini
```