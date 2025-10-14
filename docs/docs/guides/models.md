# Retrieve list of models
<p align="right">
[![](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/models.ipynb)
</p>


:::warning
For the following tutorial, we use [DINUM](https://www.numerique.gouv.fr/) instance of OpenGateLLM, called [Albert API](https://albert.api.etalab.gouv.fr/swagger). If your are not a user of this instance, please refer to the [OpenGateLLM readme](../../README.md) to install and configure your own instance.
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

Get all models information with `/v1/models` endpoint by OpenAI client.


```python
# Get all models information
models = client.models.list().data

for model in models[:3]:
    print(f"ID: {model.id}\nType: {model.type}\nOwner: {model.owned_by}\nMax tokens: {model.max_context_length}\n")
```

> ```
> ID: albert-small
> Type: text-generation
> Owner: OpenGateLLM
> Max tokens: 64000
> 
> ID: embeddings-small
> Type: text-embeddings-inference
> Owner: OpenGateLLM
> Max tokens: 8192
> 
> ID: audio-large
> Type: automatic-speech-recognition
> Owner: OpenGateLLM
> Max tokens: None
> ```

You can get only one model information with `/v1/models/\{model\}` endpoint by OpenAI client.


```python
# Get only one model information
model = client.models.retrieve(model=models[0].id)

print(f"ID: {model.id}\nType: {model.type}\nOwner: {model.owned_by}\nMax tokens: {model.max_context_length}\n")
```

> ```
> ID: albert-small
> Type: text-generation
> Owner: OpenGateLLM
> Max tokens: 64000
> ```


```python

```
