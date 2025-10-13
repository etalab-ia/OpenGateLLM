# Using a code model in an IDE

With OpenGateLLM, you can serve code models. These models can be used in the following IDEs to be used as an assistant:
- VS Code
- Intellij
- Pycharm
- Zed Editor
- Cursor

## Visual Studio Code

[Continue](https://marketplace.visualstudio.com/items?itemName=Continuestral.continue) is a Visual Studio Code plugin to use AI code agents.

After installation, please configure the plugin in `.continue/config.yml` with the following content:

```yaml
name: Local Assistant
version: 1.0.0
schema: v1
models:
  - name: OpenGateLLM
    provider: openai
    model: <YOUR_MODEL_NAME>
    apiBase: <YOUR_API_URL>
    apiKey: <YOUR_API_KEY>
    roles:
      - chat

context:
  - provider: code
  - provider: docs-legacy
  - provider: diff
  - provider: terminal
  - provider: problems
  - provider: folder
  - provider: codebase
```

## Intellij/Pycharm

[ProxyAI](https://plugins.jetbrains.com/plugin/21056-proxyai) is a Intellij/Pycharm plugin to use AI code agents.

After installation, please configure the plugin in `~/.config/ProxyAI/config.yml` with the following content:

1. Open Tool > ProxyAI > Providers    
2. Select `Custom OpenAI`  
3.Add a new configuration `+`  
4. Change the configuration:  

```yaml
name: OpenGateLLM
API Key: <YOUR_API_KEY>
URL: <YOUR_API_URL>
model: <YOUR_MODEL_NAME>
```

## Zed

[Zed](https://zed.dev/) is a code editor providing native custom IA agent providers.


1. Open the Zed Agent Panel
2. Open the Model drop-drown menu and select "Configure"
3. Select the provider OpenAI
4. Input your API Key: `<YOUR_API_KEY>`
5. Input the custom API URL : `<YOUR_API_URL>`
6. Then in the main Zed Menu, click on "Open Settings"
7. In the `"language models"` add the provider `"openai"` :

```json
"language models": {
    // maybe other models here
    "openai": {
      "api_url": "<YOUR_API_URL>",  // this should be automatically inserted
      "api_key": "<YOUR_API_KEY>",  // if not saved by the input from the Agent Panel
      "role": "chat",
      "available_models": [
        {
          "name": "<YOUR_MODEL_NAME>",
          "display_name": "<YOUR_MODEL_NAME>",
          "supports_tools": true,
          "max_tokens": <YOUR_MAX_TOKENS> // retrieve by looking at the max_context_length from /v1/models endpoint
        }
      ],
      "version": "1"
    }
  }
```

## Cursor

[Kilo Code AI Agent](https://kilocode.ai/) is a Cursor plugin to use AI code agents.

After installation, please configure the plugin with the following steps:

1. Open Kilo   
2. Select `Custom OpenAI`  
3. Add a new configuration :  

```yaml
API Key: <YOUR_API_KEY>
URL: <YOUR_API_URL>/v1/chat/completions
model: <YOUR_MODEL_NAME>
```
