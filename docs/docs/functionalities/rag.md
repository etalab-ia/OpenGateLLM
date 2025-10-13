# Retrieval-Augmented Generation (RAG)

## What is RAG
Retrieval-Augmented Generation (RAG) is a technique that combines a language model with an external knowledge source. Instead of relying only on its internal training data, the model first retrieves relevant information from a database or document store, then uses that context to generate more accurate, up-to-date, and domain-specific responses.

## How to enable RAG

To enable RAG, you need:

1. A vector store (either Qdrant or Elasticsearch).
2. An embedding model configured in config.yml.
3. Dependencies configured so OpenGateLLM can communicate with your chosen vector store.

OpenGateLLM supports two vector databases:
- [Qdrant](https://hub.docker.com/r/qdrant/qdrant)
- [Elasticsearh](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-with-docker)

### Elasticsearch
1. Add an `elasticsearch` container in the `services` section of your `compose.yml` file:

```yml
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.0.2
    restart: always
    ports:
      - "${ELASTICSEARCH_PORT:-9200}:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - "ELASTIC_USERNAME=${ELASTICSEARCH_USER:-elastic}"
      - "ELASTIC_PASSWORD=${ELASTICSEARCH_PASSWORD:-changeme}"
    volumes:
      - elasticsearch:/usr/share/elasticsearch/data
    healthcheck:
      test: [ "CMD-SHELL", "bash", "-c", ":> /dev/tcp/127.0.0.1/9200" ]
      interval: 4s
      timeout: 10s
      retries: 5
```

2. (Optional) If you need to configure authentication or port, add these lines in your `.env` file:

```
ELASTICSEARCH_PORT=<port>
ELASTIC_USERNAME=<username>
ELASTICSEARCH_HOST=<host>
ELASTIC_PASSWORD=<password>
```

:::info
The default value are:
- ELASTIC_USERNAME: elastic
- ELASTIC_PASSWORD: changeme
- ELASTICSEARCH_HOST: elastic
- ELASTICSEARCH_PORT: 9200
:::


3. Add in the `models` section your config.yml file:

```yml
models:
  [...]
  - name: embeddings-small
    type: text-embeddings-inference
    providers:
      - type: <type>
        key: <api_key_value>
        timeout: 120
        model_name: embeddings-small
```

4. Add in the `dependencies` section your config.yml file:

```yml
dependencies:
  [...]
  elasticsearch:
    hosts: http://${ELASTICSEARCH_HOST:-elasticsearch}:${ELASTICSEARCH_PORT:-9200}
    basic_auth:
      - ${ELASTIC_USERNAME:-elastic}
      - ${ELASTIC_PASSWORD:-changeme}
```

5. Add in the `settings` section your config.yml file:

```yml
settings:
  vector_store_model: embeddings-small
```

6. Run OpenGateLLM as described in:
- [running OpenGateLLM inside docker](contributing/inside-docker.mdx)
- [running OpenGateLLM outside docker](contributing/outside-docker.mdx)

### Qdrant
1. Add an `qdrant` container in the `services` section of your `compose.yml` file:

```yml
  qdrant:
    image: qdrant/qdrant:v1.11.5-unprivileged
    restart: always
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY:-changeme}
    volumes:
      - qdrant:/qdrant/storage
    ports:
      - ${QDRANT_HTTP_PORT:-6333}:6333
      - ${QDRANT_GRPC_PORT:-6334}:6334
    healthcheck:
      test: [ "CMD-SHELL", "bash", "-c", ":> /dev/tcp/127.0.0.1/${QDRANT_HTTP_PORT:-6333}" ]
      interval: 4s
      timeout: 10s
      retries: 5
```

2. (Optional) If you need to configure authentication or port, add these lines in your `.env` file:

```
QDRANT_HTTP_PORT=<http_port>
QDRANT_GRPC_PORT=<grpc_port>
QDRANT_API_KEY=<password>
QDRANT_HOST=<host>
```

:::info
The default value are:
- QDRANT_API_KEY: changeme
- QDRANT_HTTP_PORT: 6333
- QDRANT_GRPC_PORT: 6334
:::


3. Add in the `models` section your config.yml file:

```yml
models:
  [...]
  - name: embeddings-small
    type: text-embeddings-inference
    providers:
      - type: <type>
        key: <api_key_value>
        timeout: 120
        model_name: embeddings-small
```

4. Add in the `dependencies` section your config.yml file:

```yml
dependencies:
  [...]
    qdrant:
      url: "http://${QDRANT_HOST:-qdrant}:${QDRANT_HTTP_PORT:-6333}"
      api_key: ${QDRANT_API_KEY:-changeme}
      prefer_grpc: False
      grpc_port: ${QDRANT_GRPC_PORT:-6334}
      timeout: 20
```

5. Add in the `settings` section your config.yml file:

```yml
settings:
  vector_store_model: embeddings-small
```

6. Run OpenGateLLM as described in [quickstart](../getting-started/quickstart.md