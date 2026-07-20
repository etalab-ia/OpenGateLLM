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