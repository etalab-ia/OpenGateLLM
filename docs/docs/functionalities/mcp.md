# Model Context Protocol (MCP)
## What is MCP?

The **Model Context Protocol (MCP)** is a standardized framework designed to connect **Language Models (LLMs)** with **external tools, APIs, or data sources** in a seamless and interoperable way.
It defines a common structure for **exchanging context** between the model and these resources, allowing the LLM to:

* Dynamically fetch or update information during a conversation.
* Access specialized capabilities or private datasets.
* Generate **context-aware**, **actionable**, and **up-to-date** responses.

In short, MCP turns a static LLM into an **interactive, connected AI agent** capable of reasoning over both internal and external knowledge.

## How OpenGateLLM Uses MCP

**OpenGateLLM** integrates MCP to give developers a powerful way to plug their LLM workflows into any MCP-compatible service.
The connection between OpenGateLLM and MCP Servers is made possible via an **MCP Bridge** component, which acts as the “translator” between the protocol and OpenGateLLM’s internal gateway system.

### Used MCP Bridge

* **Repository**: [SecretiveShell/MCP-Bridge](https://github.com/SecretiveShell/MCP-Bridge)
* **Role**: Handles communication between OpenGateLLM and any MCP Server, translating requests/responses into a format the model understands.

## How to enable MCP in OpenGateLLM

To activate **MCP** support in **OpenGateLLM**, you need to add a dedicated **MCP Bridge service** in your `docker-compose.yml` configuration.
This bridge is responsible for connecting the OpenGateLLM Gateway to an MCP Server.


1. Add the MCP Bridge service to `docker-compose.yml`

```yaml
services:
  [..]
  secretiveshell:
    image: ghcr.io/etalab-ia/albert-api-mcp-bridge/albert-api-mcp-bridge:latest
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: always
    ports:
      - "${SECRETIVESHELL_PORT:-8000}:8000"
    environment:
      - MCP_BRIDGE__CONFIG__FILE=config.json
    volumes:
      - <path_to_mcp_config_file>/mcp_config.json:/mcp_bridge/config.json
```

2. (Optional) Define environment variables in `.env`

The MCP Bridge requires a few global variables.
Add them to your `.env` file (or update existing ones):

```env
SECRETIVESHELL_PORT=8000
```

---

3. Prepare your MCP servers configuration

The file `mcp_config.json` contains the bridge configuration.
Example minimal config:

```json
{
    "mcp_servers": {
        "data-gouv": {
            "command": "uvx",
            "args": [
                "data-gouv-fr-mcp-server"
            ]
        }
}}
```

4. You can set the number of llm calls in the config.file:
```yml
settings:
  mcp_max_iterations: 2
```

6. Run OpenGateLLM as described in:
- [running OpenGateLLM inside docker](contributing/inside-docker.mdx)
- [running OpenGateLLM outside docker](contributing/outside-docker.mdx)



## Benefits of MCP Integration in OpenGateLLM

* **Vendor-Agnostic** – Works with any MCP-compliant server or tool.
* **Dynamic Context Injection** – Fetch real-time data or execute actions mid-conversation.
* **Security-First Design** – Explicitly controls what tools the LLM can access.
* **Extensibility** – Easily add new MCP tools without modifying your LLM code.

