# Identity and Access Management

## Overview

OpenGateLLM implements a security system based on users, roles, and permissions. This documentation explains how to manage security within the system, with special focus on the master key, user authentication, and role-based access control.

## Authentication System

The security model consists of three main components:
- Roles: Define sets of permissions and usage limits
- Users: Entities that can access the API with assigned roles
- Tokens: API keys that authenticate user requests

## Master Key

### What is the Master Key?

The master key is a special API key that:
- Is used for initial system setup
- Grants access to the API with unlimited permissions
- Encrypts all user tokens for security
- Cannot be modified or deleted through the API

### Configuration

The master key is defined in the auth section of the configuration file:

```yaml
auth:
  master_username: "master"
  master_key: "changeme"
```

> **❗️Note**<br>
> The default values `master_username` and `master_key` should be replaced with a strong, unique secret key in production environments.

[See configuration documentation for more information](./deployment.md#auth)

## Using the Master Key

The master key serves several critical purposes:
- Initial System Setup: When the database is empty, the master user can create the first roles and users
- Emergency Access: Provides a failsafe way to access the system if regular authentication fails
- Token Encryption: Used to encrypt all user tokens, ensuring they cannot be compromised

> **⚠️ Warning**<br>
> If you modify the master key, you'll need to update all user API keys since they're encrypted using this key.

## Login (verify_user_credentials)

The codebase exposes a helper used for the interactive Playground (and other UI logins) named `verify_user_credentials`.

- Purpose: verify a user's email and password against the stored FastAPI user record.
- Inputs: an email and a plaintext password.
- Behavior: the function looks up the user by `email`, reads the stored (bcrypt) hashed password and compares it using `bcrypt.checkpw`.
- Returns: on success it returns the ORM user object (the underlying FastAPI `UserTable` instance). On failure it returns `None`.

Notes:
- In the Playground (Streamlit) UI the `playground_name` maps to the FastAPI `user.email` field — this is what `verify_user_credentials` checks.
- If a user record doesn't exist, or the user has no stored password, or the password check fails, the function returns `None` and the login is rejected.

This function is intentionally lightweight: it does not issue tokens itself — it only verifies credentials. Token creation is done through the token management endpoints/helpers.

Examples

- Login with email/password (Playground):

```bash
curl -s -X POST "http://localhost:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "your_password"}'
```

Expected successful response (JSON):

```json
{
  "status": "success",
  "api_key": "sk-<full-token-string>",
  "token_id": 123,
  "user_id": 1
}
```

- Use the returned API key in subsequent requests (Authorization header):

```bash
curl -s "http://localhost:8000/v1/auth/me" \
  -H "Authorization: Bearer sk-<full-token-string>"
```

The Playground front-end stores `api_key` in session state and sends it as `Authorization: Bearer <api_key>` for later requests.

## Role Management

Roles define what actions users can perform within the system through permissions, and what resource limits apply.

### Role Properties

- Name: unique identifier for the role
- Default: whether this is the default role assigned to new users (for Playground UI)
- Permissions: list of actions the role can perform
- Limits: resource usage limits for users with this role

> **❗️Note**<br>
> All permissions and limits are managed by the *[Authorization](../api/helpers/_authorization.py)* class.

### Available Permissions

| Permission               | Description |
| ------------------------ | ----------- |
| CREATE_ROLE              | Create a new role |
| READ_ROLE                | Read a role |
| UPDATE_ROLE              | Update a role |
| DELETE_ROLE              | Delete a role |
| CREATE_USER              | Create a new user and a token for other users |
| READ_USER                | Read a user |
| UPDATE_USER              | Update a user |
| DELETE_USER              | Delete a user |
| CREATE_PUBLIC_COLLECTION | Create a public collection |
| READ_METRIC              | Read prometheus `/metrics` endpoint |

### Limits

Limits define model usage limits for users with this role. A limit is a tuple of `model`, `type` and `value`.

Example: `("gpt-4o", "TPM", 1000)`

The `type` can be:
- `TPM`: tokens per minute
- `RPM`: requests per minute
- `TPC`: tokens per collection
- `RPC`: requests per collection

If value is `None`, the limit is not applied.

### Managing Roles

The API provides endpoints to:
- Create roles (POST `/v1/admin/roles`)
- View roles (GET `/v1/admin/roles`, GET `/v1/admin/roles/{role_id}`)
- Update roles (PATCH `/v1/admin/roles/{role_id}`)
- Delete roles (DELETE `/v1/admin/roles/{role_id}`)

*Example role creation:*

```json
POST /v1/admin/roles
{
  "name": "Admin",
  "default": false,
  "permissions": ["CREATE_USER", "READ_USER", "UPDATE_USER", "DELETE_USER"],
  "limits": [
    {
      "model": "my-language-model",
      "type": "tpm",
      "value": 100000
    }
  ]
}
```

## User Management

Users represent entities that can access the API.

### User Properties

- Name: Username for identification
- Role: The assigned role ID that determines permissions and limits
- Expires At: Optional timestamp when the user account expires

### Managing Users

The API provides endpoints to:
- Create users (POST `/v1/admin/users`)
- View users (GET `/v1/admin/users`, GET `/v1/admin/users/{user_id}`)
- Update users (PATCH `/v1/admin/users/{user_id}`)
- Delete users (DELETE `/v1/admin/users/{user_id}`)

*Example user creation:*

```json
POST /v1/admin/users
{
  "name": "john_doe",
  "role": 1,
  "expires_at": 1735689600  // Optional, Unix timestamp
}
```

## Token Management

Tokens are the API keys used to authenticate requests.

### Token Properties

- Name: Descriptive name for the token
- Expires At: Optional timestamp when the token expires

### Managing Tokens

The API provides endpoints to:

- Create tokens (POST `/v1/admin/tokens`)
- View tokens (GET `/v1/admin/tokens`, GET `/v1/admin/tokens/{token_id}`)
- Delete tokens (DELETE `/v1/admin/tokens/{token_id}`)

Example token creation:

```json
POST /v1/admin/tokens
{
  "name": "Development API Key",
  "expires_at": 1704067200  // Optional, Unix timestamp
}
```

> **❗️Note**<br>
> `CREATE_USER` permission allows to create tokens for other users with `user` field in the request body of POST `/v1/admin/tokens`. These tokens are not subject to the `max_token_expiration_days` limit set in the auth section of the configuration file.

### Refreshing tokens (refresh_token)

There is a helper called `refresh_token` used by the Playground (Streamlit front-end) to renew a token with a given name for a user. The behavior is:

- Inputs: `user_id`, `name` (token name), and optional `days` (validity of the new token, default 1 day).
- Operation sequence:
  1. Find any existing tokens for the given `user_id` and `name` and collect their ids.
  2. Create a brand new token using the same `name` and the computed `expires_at` (based on `days`). Internally this calls `create_token`, which returns the new `token_id` and the full encoded app token (the secret string the client will use).
  3. Update any existing `Usage` records that referenced the old token ids to point to the new `token_id` so usage history remains consistent.
  4. Delete the old tokens that matched the `user_id` and `name` (the newly created token is kept).
  5. Commit the changes and return the `new_token_id` and the full new app token.

Notes and implications:
- The new token returned by `refresh_token` is the real API key (encoded with the master key); the value stored in the database is a masked preview (for example: `sk-XXXXXXXX...YYYYYYYY`) so the full secret is only available once when created.
- `refresh_token` is convenient for the Playground: it replaces any existing token with the same name, migrates usage references, and provides the client with a new secret to use in subsequent requests.
- Because `refresh_token` ultimately uses `create_token`, the `max_token_expiration_days` configuration (if set) applies when the token is created.

Where it's used in the app

- `/v1/auth/login` (Playground login): the `/v1/auth/login` endpoint calls `refresh_token` after verifying the user's credentials. This returns a fresh playground API key to the client so the UI can immediately use it for authenticated requests.
- ProConnect OAuth2 callback (`/v1/auth/callback`): the ProConnect flow also calls `refresh_token` after exchanging the OAuth2 code and creating/finding the corresponding user. The callback then issues the new token back to the browser (usually via an encrypted redirect) so the user is logged into the Playground after OAuth login.

Because both the explicit Playground login and the ProConnect callback call `refresh_token`, a new playground token is generated and returned on each successful authentication. Old tokens with the same name are removed (and their usage references migrated), so the Playground always receives a single fresh token for the `playground` name after login.

