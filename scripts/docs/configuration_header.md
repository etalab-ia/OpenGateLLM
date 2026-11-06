---
title: Configuration file
sidebar:
  label: "[lucide:file-text] Configuration file"
  order: 0
---
import { Badge, Tabs, TabItem } from '@astrojs/starlight/components';
import ConfigTableDocs from '../../../components/ConfigTableDocs.astro';

<ConfigTableDocs />

OpenGateLLM requires configuring a configuration file. This defines models, dependencies, and settings parameters. Playground and API can share the same configuration file; the **Scope** column in each table indicates whether a field applies to the API, the Playground, or both.

By default, the configuration file must be `./config.yml` file.

You can change the configuration file by setting the `CONFIG_FILE` environment variable.

## Secrets

You can pass environment variables in configuration file with pattern `${ENV_VARIABLE_NAME}`, in any value of the file. The value of a variable is used as it is, whatever its characters: it can not hold YAML structure.

| Pattern | When the variable is missing or empty |
|---|---|
| `${ENV_VARIABLE_NAME}` | The application refuses to start, with an error naming the variable |
| `${ENV_VARIABLE_NAME:-default}` | `default` is used |
| `${ENV_VARIABLE_NAME:-}` | An empty string is used |

A name only holds uppercase letters, digits and underscores. Any other `${...}` also stops the application.

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
