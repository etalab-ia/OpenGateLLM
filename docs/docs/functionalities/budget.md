import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Budget

OpenGateLLM allows you to define the costs for each model in the `config.yml` file then attach a budget to each user.

## Model costs

For each model provider, you can define the costs of each model in the `config.yml` file for the prompt and completion tokens (per million tokens). 

The following parameters are used for cost computation:
- `model_cost_prompt_tokens`
- `model_cost_completion_tokens`

For more information, see [Configuration](../getting-started/configuration.md) documentation.

**Example:**

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
        model_cost_prompt_tokens: 0.1
        model_cost_completion_tokens: 0.3
```

## User budget

Each user has a budget defined by create user endpoint or update user endpoint. The budget is defined in the `budget` field. You need has `admin` permission to create or update a user (see [Identity and access management](./iam.md) documentation).

<Tabs>
  <TabItem value="Create user" label="Create user" default>
  ```bash
    curl -X POST http://localhost:8000/v1/admin/users \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
        "email": "john.doe@example.com",
        "role": 1,
        "budget": 100
    }'
    ```
  </TabItem>
  <TabItem value="Update user" label="Update user">
  ```bash
    curl -X PATCH http://localhost:8000/v1/admin/users/1 \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
        "budget": 100
    }'
    ```
    </TabItem>
</Tabs>

:::info
If budget is not defined, the user has no limit on the number of requests.
:::

## How it works

The compute cost is calculated based on the number of tokens used and the budget defined for the model based on the following formula:

```python
cost = round((prompt_tokens / 1000000 * client.costs.prompt_tokens) + (completion_tokens / 1000000 * client.costs.completion_tokens), ndigits=6)
```

The compute cost returned in the response, in the `usage.cost` field. After the request is processed, the budget amount of the user is updated by the [hooks decorator](https://github.com/etalab-ia/OpenGateLLM/blob/main/api/utils/hooks_decorator.py) attached to each endpoint. The request cost is stored in the *usage* table, see [usage monitoring documentation](./usage.md) for more information. 