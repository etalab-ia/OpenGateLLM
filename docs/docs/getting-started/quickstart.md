# Quickstart

You can run OpenGateLLM without any configuration with Docker.
```bash
make quickstart
```

:::note
It will copy these three files if they don't already exist:
- `config.example.yml`      -> `config.yml`
- `.env.example`            -> `.env`
- `compose.example.yml`     -> `compose.yml`
:::

:::tip
Use `make help` to see all available commands.
:::

OpenGateLLM is running at its most basic version, with the following features:
- an api connected to our free model: `albert-testbed`
- an user interface
- user and roles management

:::info
| | |
|----------|-------------|
| API URL | http://localhost:8080   |
| Playground URL | http://localhost:8081/playground |
| Master user | master |
| Master user password | changeme |
| Master API key | changeme |
:::


You can test that the API is running with:

```bash 
curl -X POST "http://localhost:8080/v1/chat/completions" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer changeme" \
-d '{"model": "albert-testbed", "messages": [{"role": "user", "content": "Hello, how are you?"}]}'
```

:::warning
`albert-testbed` is a gemma3 model, running on cpu. It is not meant for production use, only dev purposes.
:::


### Create a first user

You can create a non-admin user with the following command:
```bash
make create-user
```
The default created user will be `me` and its password `changeme`.