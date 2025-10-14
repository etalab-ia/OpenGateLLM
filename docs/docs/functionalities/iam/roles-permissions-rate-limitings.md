import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Role, permissions and rate limitings

Roles define what actions users can perform within the system through permissions, and what resource limits apply through rate limiting.

## Available permissions

| Permission               | Description                           |
| ------------------------ | ------------------------------------- |
| `admin`                  | Full administrative access            |
| `create_public_collection` | Create public collections           |
| `read_metric`            | Read prometheus `/metrics` endpoint   |
| `provide_models`         | Provide models to the system          |

## Rate limiting

Rate limiting controls model usage for users with a specific role. Each limit has three components defined in the `limits` parameter:
- `model`: The model name
- `type`: The limit type
- `value`: The limit value (if `null`, the limit is not applied)

:::tip
Rate limiting allow to control model access. If a limit is set to `0`, the model will be inaccessible.
:::

### Available limit types

| Limit Type | Description              |
| ---------- | ------------------------ |
| `tpm`      | Tokens per minute        |
| `tpd`      | Tokens per day           |
| `rpm`      | Requests per minute      |
| `rpd`      | Requests per day         |

**Example:**

```json
{
  "model": "my-language-model",
  "type": "tpm",
  "value": 100000
}
```

:::info
Rate limiting requires Redis to be configured. For more information about Redis setup and rate limiting strategies, see [Redis documentation](../../dependencies/redis.md#rate-limiting).
:::

## Managing roles

<Tabs>
  <TabItem value="Create role" label="Create role" default>
  ```bash
  curl -X POST http://localhost:8000/v1/admin/roles \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Developer",
      "permissions": ["create_public_collection"],
      "limits": [
        {
          "model": "my-language-model",
          "type": "tpm",
          "value": 100000
        }
      ]
    }'
  ```
  </TabItem>
  <TabItem value="Get roles" label="Get roles">
  ```bash
  curl -X GET http://localhost:8000/v1/admin/roles \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get role by ID" label="Get role by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/admin/roles/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Update role" label="Update role">
  ```bash
  curl -X PATCH http://localhost:8000/v1/admin/roles/1 \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Senior Developer",
      "permissions": ["create_public_collection", "read_metric"]
    }'
  ```
  </TabItem>
  <TabItem value="Delete role" label="Delete role">
  ```bash
  curl -X DELETE http://localhost:8000/v1/admin/roles/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

