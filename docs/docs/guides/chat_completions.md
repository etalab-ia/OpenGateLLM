# Chat completions
<p align="right">
[![](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/chat_completions.ipynb)
</p>


:::warning
For the following tutorial, we use [DINUM](https://www.numerique.gouv.fr/) instance of OpenGateLLM, called [Albert API](https://albert.api.etalab.gouv.fr/swagger). If your are not a user of this instance, please refer to the [OpenGateLLM readme](https://github.com/etalab-ia/OpenGateLLM?tab=readme-ov-file#-tutorials--guides) to install and configure your own instance. You need to have a text-generation or image-text-to-text model to run this tutorial.
:::


```python
%pip install -qU openai

import os

from openai import OpenAI
```

First, setup your API key in the environment variable `ALBERT_API_KEY` for OpenAI client.


```python
base_url = "https://albert.api.etalab.gouv.fr/v1"
api_key = os.getenv("ALBERT_API_KEY")
client = OpenAI(base_url=base_url, api_key=api_key)
```

Retrieve the list of available models with `/v1/models` endpoint for chat completions. Theses models have the type `text-generation` or `image-text-to-text`.


```python
models = client.models.list().data

model = [model for model in models if model.type in ["text-generation", "image-text-to-text"]][0].id
print(f"Chat model found: {model}")
```

> ```
> Chat model found: albert-small
> ```

### Unstreamed chat

Run a unstreamed chat with `/v1/chat/completions` endpoint by OpenAI client.


```python
data = {
    "model": model,
    "messages": [{"role": "user", "content": "Hi Albert !"}],
    "stream": False,
    "n": 1,
}

response = client.chat.completions.create(**data)
print(f"Chat result: {response.choices[0].message.content}")
```

> ```
> Chat result: Hello there! Unfortunately, I'm not Albert Einstein, but I'll do my best to help you with any questions or topics you'd like to discuss. How can I assist you today?
> ```

### Streamed chat

Run a streamed chat with `/v1/chat/completions` endpoint by OpenAI client.


```python
# streamed chat
data = {
    "model": model,
    "messages": [{"role": "user", "content": "What's up Albert ?"}],
    "stream": True,
    "n": 1,
}

response = client.chat.completions.create(**data)
print("Chat result:")
for chunk in response:
    if chunk.choices[0].finish_reason is not None:
        break
    print(chunk.choices[0].delta.content, end="\ntoken: ", flush=True)
```

> ```
> Chat result:
> 
> token: Not
> token:  much
> token: .
> token:  Just
> token:  here
> token:  to
> token:  help
> token:  answer
> token:  any
> token:  questions
> token:  or
> token:  chat
> token:  with
> token:  you
> token: .
> token:  What
> token: 's
> token:  on
> token:  your
> token:  mind
> token: ?
> token:
> ```