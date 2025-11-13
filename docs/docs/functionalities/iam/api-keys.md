import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# API Keys

API keys are used to authenticate requests to the OpenGateLLM API. Each user can have multiple API keys for different purposes.

## Master Key

The master key is a special administrative API key defined in your configuration file, used to encrypt user API keys. For details on configuring the master key, see [Master Key Configuration](./index.md#master-key-configuration).

## API key properties

- `name`: Descriptive name for the API key (required)
- `user`: User ID to create the API key for (required, must have `ADMIN` permission)
- `expires`: Unix timestamp when the API key expires (optional)

:::warning
The API key is only shown once when created. Make sure to save it securely. You will not be able to retrieve the full key value again.
:::

## Managing API keys

<Tabs>
  <TabItem value="Create API key" label="Create API key" default>
  ```bash
  curl -X POST http://localhost:8000/v1/admin/tokens \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Development API Key",
      "user": 1,
      "expires": 1735689600
    }'
  ```
  </TabItem>
  <TabItem value="Get API keys" label="Get API keys">
  ```bash
  curl -X GET "http://localhost:8000/v1/admin/tokens?user=1&offset=0&limit=10&order_by=id&order_direction=asc" \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get API key by ID" label="Get API key by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/admin/tokens/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Delete API key" label="Delete API key">
  ```bash
  curl -X DELETE http://localhost:8000/v1/admin/tokens/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

## API key format

API keys in OpenGateLLM follow the format: `sk-<encoded_token>`

The token is a JWT (JSON Web Token) that contains:
- `user_id`: The ID of the user who owns the key
- `token_id`: The unique identifier for this specific API key
- `expires`: The expiration timestamp (if set)
