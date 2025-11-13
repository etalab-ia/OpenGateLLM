import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Organizations, projects, and users

This section covers how to manage organizational structure and user accounts within OpenGateLLM.

## Organization management

Organizations allow grouping users for organizational purposes.

### Organization properties

- `name`: Organization name (required)

### Managing organizations

<Tabs>
  <TabItem value="Create organization" label="Create organization" default>
  ```bash
  curl -X POST http://localhost:8000/v1/admin/organizations \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "My Organization"
    }'
  ```
  </TabItem>
  <TabItem value="Get organizations" label="Get organizations">
  ```bash
  curl -X GET "http://localhost:8000/v1/admin/organizations?offset=0&limit=10&order_by=id&order_direction=asc" \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get organization by ID" label="Get organization by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/admin/organizations/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Update organization" label="Update organization">
  ```bash
  curl -X PATCH http://localhost:8000/v1/admin/organizations/1 \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "New Organization Name"
    }'
  ```
  </TabItem>
  <TabItem value="Delete organization" label="Delete organization">
  ```bash
  curl -X DELETE http://localhost:8000/v1/admin/organizations/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

## Project management

:::warning Coming Soon
Project management functionality is currently under development and will be available in a future release.
:::

Projects will allow you to:
- Group resources within an organization
- Isolate access and permissions at the project level
- Manage project-specific budgets and limits

## User management

Users represent entities that can access the API. Each user must have an email, password, and assigned role.

### User properties

- `email`: User email address (required)
- `name`: User display name (optional)
- `password`: User password for authentication (required on creation)
- `role`: Role ID that determines permissions and limits (required)
- `organization`: Organization ID (optional)
- `budget`: Budget limit for the user (optional, see [Budget](../budget.md))
- `expires`: Unix timestamp when the user account expires (optional)

:::info
Users also have `sub` and `iss` fields for OAuth2/ProConnect authentication. These are `null` when using email/password authentication.
:::

### Managing users

<Tabs>
  <TabItem value="Create user" label="Create user" default>
  ```bash
  curl -X POST http://localhost:8000/v1/admin/users \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "email": "john.doe@example.com",
      "name": "John Doe",
      "password": "secure_password",
      "role": 1,
      "organization": 1,
      "budget": 100.0,
      "expires": 1735689600
    }'
  ```
  </TabItem>
  <TabItem value="Get users" label="Get users">
  ```bash
  curl -X GET "http://localhost:8000/v1/admin/users?role=1&organization=1&offset=0&limit=10&order_by=id&order_direction=asc" \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Get user by ID" label="Get user by ID">
  ```bash
  curl -X GET http://localhost:8000/v1/admin/users/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
  <TabItem value="Update user" label="Update user">
  ```bash
  curl -X PATCH http://localhost:8000/v1/admin/users/1 \
    -H "Authorization: Bearer <api_key>" \
    -H "Content-Type: application/json" \
    -d '{
      "email": "new.email@example.com",
      "name": "John Smith",
      "budget": 200.0
    }'
  ```
  </TabItem>
  <TabItem value="Delete user" label="Delete user">
  ```bash
  curl -X DELETE http://localhost:8000/v1/admin/users/1 \
    -H "Authorization: Bearer <api_key>"
  ```
  </TabItem>
</Tabs>

