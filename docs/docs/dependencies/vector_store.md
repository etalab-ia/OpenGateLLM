import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Vector Store

OpenGateLLM allows you to interact with a vector database to perform [RAG (Retrieval-Augmented Generation)](https://en.wikipedia.org/wiki/Retrieval-augmented_generation). The API lets you feed this vector store by importing files, which are automatically processed and inserted into the database.

## Setup a vector store

OpenGateLLM supports currently two vector databases:
- [Qdrant](https://qdrant.tech/documentation/guides/installation/#docker-and-docker-compose)
- [Elasticsearh](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-with-docker)

### Prerequisites

To enable the vector store, you need:

1. A vector database (either Qdrant or Elasticsearch)
2. An embedding model

### Configuration

<Tabs>
  <TabItem value="elasticsearch" label="Elasticsearch" default>

#### Docker compose

Add an `elasticsearch` container in the `services` section of your `compose.yml` file:

```yaml
services:
  [...]
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:9.0.2
    restart: always
    ports:
      - "${ELASTICSEARCH_PORT:-9200}:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - "ELASTIC_USERNAME=${ELASTICSEARCH_USER:-elasticsearch}"
      - "ELASTIC_PASSWORD=${ELASTICSEARCH_PASSWORD:-changeme}"
    volumes:
      - elasticsearch:/usr/share/elasticsearch/data
    healthcheck:
      test: [ "CMD-SHELL", "bash", "-c", ":> /dev/tcp/127.0.0.1/9200" ]
      interval: 4s
      timeout: 10s
      retries: 5
```

#### Configuration file

:::info
For more information about the configuration file, see [Configuration](../getting-started/configuration.md) documentation.
:::

1. Add Elasticsearch in the `dependencies` section of your `config.yml`. Example:

    ```yaml
    dependencies:
      elasticsearch:
        hosts: http://${ELASTICSEARCH_HOST:-elasticsearch}:${ELASTICSEARCH_PORT:-9200}
        basic_auth:
          - ${ELASTIC_USERNAME:-elasticsearch}
          - ${ELASTIC_PASSWORD:-changeme}
    ```

2. Add a model provider for a model with `text-embeddings-inference` type in the `models` section of your `config.yml`. Example:

    ```yaml
    models:
      [...]
      - name: embeddings-small
        type: text-embeddings-inference
        providers:
          - type: openai
            key: ${OPENAI_API_KEY}
            timeout: 120
            model_name: text-embedding-3-small
    ```

    This model will be used to vectorize the text in the vector store database.

3. Specify the vector store model in the `settings` section of your `config.yml`.

    ```yaml
    settings:
      vector_store_model: embeddings-small
    ```

  </TabItem>
  <TabItem value="qdrant" label="Qdrant">

#### Docker Compose

Add a `qdrant` container in the `services` section of your `compose.yml` file:

```yaml
services:
  [...]
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

#### Configuration file

:::info
For more information about the configuration file, see [Configuration](../getting-started/configuration.md) documentation.
:::

1. Add an embedding model in the `models` section of your `config.yml`. Example:

    ```yaml
    models:
      [...]
      - name: embeddings-small
        type: text-embeddings-inference
        providers:
          - type: openai
            key: ${OPENAI_API_KEY}
            timeout: 120
            model_name: text-embedding-3-small
    ```

2. Add Qdrant in the `dependencies` section of your `config.yml`. Example:

    ```yaml
    dependencies:
      qdrant:
        url: "http://${QDRANT_HOST:-qdrant}:${QDRANT_HTTP_PORT:-6333}"
        api_key: ${QDRANT_API_KEY:-changeme}
        prefer_grpc: False
        grpc_port: ${QDRANT_GRPC_PORT:-6334}
        timeout: 20
    ```

This model will be used to vectorize the text in the vector store database.

3. Specify the vector store model in the `settings` section of your `config.yml`.

    ```yaml
    settings:
      vector_store_model: embeddings-small
    ```

  </TabItem>
</Tabs>

## Access to the vector store

When the vector store is enabled, you can access to the document management endpoints to perform Retrieval-Augmented Generation (RAG):
- `/v1/collections`
- `/v1/documents`
- `/v1/chunks`

For more information about the document management, see [Retrieval-Augmented Generation (RAG) documentation](../functionalities/rag.md).