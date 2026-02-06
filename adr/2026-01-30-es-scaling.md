# ADR - 2026-01-30 - Elasticsearch Scaling

**Status:** Accepted
**Date:** 2026-01-30
**Authors:** Development Team
**Decision Outcome:** Merge Elasticsearch indices into a single index

---

## Context

Currently, we support two vector store technologies: Qdrant and Elasticsearch. A few months ago, we decided to focus on Elasticsearch for managing our document collections. We revisit the reasons for this choice here.

However, over the past few weeks, we have encountered scalability issues with Elasticsearch. These problems stem from how we implemented Elasticsearch in OpenGateLLM. To resolve these issues, we decided to revise our approach, which involves major changes and a data migration.

To this end, we detail the modifications we have made and provide a migration script to help you update your instance.

### Why Elasticsearch over Qdrant?

In Retrieval-Augmented Generation (RAG), there are 3 classic search methods:
* Lexical search with BM25 (TF-IDF)
* Semantic search with vector similarity
* Hybrid search combining both (using the Reciprocal Rank Fusion (RRF) algorithm to combine results)

We sought to offer these 3 search methods to our users. Initially, we implemented Qdrant for semantic search due to its scalability.

However, when wanting to add lexical and hybrid search, we found that Qdrant does not natively support these methods. [Their approach](https://qdrant.tech/documentation/concepts/inference/) is based on deploying a model alongside the vector store.

Additionally, Elasticsearch excels at lexical search with BM25 and natively enables complex filtering on specific fields. For these reasons, Elasticsearch seems like a better solution for RAG search.

OpenGateLLM's goal is to support multiple vector store solutions to give you the choice of the technology that best suits your needs.

## Decisions

### End of Qdrant Support

To focus on Elasticsearch support, we have decided to deprecate Qdrant support. This decision was made after consulting the community on the subject. Indeed, it turns out that currently, no one has chosen Qdrant for their OpenGateLLM instance.

Additionally, with the OpenGateLLM team having limited resources, we cannot afford to maintain two vector store solutions at this time.

We do not rule out revisiting this decision in the future if the community requests it. Moreover, the goal remains to support multiple vector store solutions in the long term, once we have the necessary resources.

### Consolidation of Elasticsearch Indices into a Single Index

Currently, OpenGateLLM creates an Elasticsearch index for each collection. This approach allows collections to be managed independently. However, this is not optimal for scalability. Indeed, by default, Elasticsearch limits the number of shards (for each index, Elasticsearch creates at least one shard). The multiplication of indices can quickly become a performance bottleneck in this context.

>*A good rule-of-thumb is to ensure you keep the number of shards per node below 20 per GB heap it has configured. A node with a 30GB heap should therefore have a maximum of 600 shards, but the further below this limit you can keep it the better. [Source: How many shards should I have in my Elasticsearch cluster?](https://www.elastic.co/blog/how-many-shards-should-i-have-in-my-elasticsearch-cluster)*

To solve this problem, we decided to consolidate all Elasticsearch indices into a single index. To migrate your data, we provide a migration script (see [Migration Script](#migration-script)).

### Convert document metadata into a single field with constraints

Currently, when creating a document, users can define metadata for the document. They are free to define any metadata they want with the following types: `int`, `str`, `float`, `datetime`, or `bool`. Each metadata is stored in a separate field in the Elasticsearch index. This dynamic addition of metadata will quickly become problematic with the consolidation of indices into a single index. Indeed, Elasticsearch is not designed to optimally support thousands of fields on an index. This risks creating performance and scalability issues.

To address this issue, we decided to convert the metadata field into a single field of type `flattened`. However, this solution limits filtering actions on these fields (they are then stored in a single field and interpreted as `str`), see [Elasticsearch documentation](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/flattened). However, the tests we have performed have shown that the filtering capabilities on a `flattened` field seem sufficient for RAG search operations.

Additionally, at the Pydantic level, we have added constraints on the types of data that can be stored in the metadata field.

From now on, the metadata field must comply with the following constraints:

```python
MIN_NUMBER, MAX_NUMBER = -9999999999999999, 9999999999999999

MetadataStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
MetadataInt = Annotated[int, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataFloat = Annotated[float, Field(ge=MIN_NUMBER, le=MAX_NUMBER)]
MetadataList = Annotated[list[MetadataStr | MetadataInt | MetadataFloat | bool | None], Field(max_length=8)]

ChunkMetadata = Annotated[dict[MetadataStr, MetadataStr | MetadataInt | MetadataFloat | MetadataList | bool | None], Field(description="Extra metadata for the source", min_length=1, max_length=8)]
```

One possible solution would have been to define fields with the `flattened` type. However, this solution only partially solves the performance problem and limits filtering actions on these fields (they are then stored in a single field and interpreted as `str`).

To ensure the scalability of the Elasticsearch index, we decided to pre-define metadata for documents. This approach avoids overloading the index with metadata while maintaining type-based filtering capabilities.

## Migration script

The [`adr/scripts/2026-01-30-es-migration.py`](adr/scripts/2026-01-30-es-migration.py) script is used to migrate the data from the source Elasticsearch indices to the destination Elasticsearch index.

1. Clone the repository on the target server

```bash
git clone https://github.com/etalab-ia/OpenGateLLM.git && cd OpenGateLLM
```

2. Install the dependencies

> [!NOTE]
> We recommend to create a virtual environment and activate it before installing the dependencies.

```bash
pip install ".[api]"
```

3. Create the bash script to run the migration

```bash
touch run.sh
```

The script should look like this:

```bash
#!/bin/bash
export PYTHONPATH=.
export POSTGRES_URL=

export SOURCE_ES_URL=
export SOURCE_ES_USERNAME=
export SOURCE_ES_PASSWORD= 

export DESTINATION_ES_URL=
export DESTINATION_ES_USERNAME=
export DESTINATION_ES_PASSWORD=
export DESTINATION_ES_INDEX_NAME=
export DESTINATION_ES_VECTOR_SIZE=
export DESTINATION_ES_NUMBER_OF_SHARDS=
export DESTINATION_ES_NUMBER_OF_REPLICAS=
export DESTINATION_ES_INDEX_LANGUAGE=

python adr/scripts/2026-01-30-es-migration.py > migration.log 2>&1
```

The environment variables are:

| Variable | Description | Example |
|----------|-------------|-------------|
| `POSTGRES_URL` | The URL of the PostgreSQL database. The URL must be in the format `postgresql+asyncpg://<username>:<password>@<host>:<port>/<database>`. | `postgresql+asyncpg://postgres:changeme@localhost:5432/postgres` |
| `SOURCE_ES_URL` | The URL of the source Elasticsearch cluster must be in the format `http://<host>:<port>`. You can use the same Elastiscearch cluster for the source and destination. | `http://localhost:9200` |
| `SOURCE_ES_USERNAME` | The username of the source Elasticsearch cluster. | `elasticsearch` |
| `SOURCE_ES_PASSWORD` | The password of the source Elasticsearch cluster. | `changeme` |
| `DESTINATION_ES_URL` | The URL of the destination Elasticsearch cluster must be in the format `http://<host>:<port>`. | `http://localhost:9200` |
| `DESTINATION_ES_USERNAME` | The username of the destination Elasticsearch cluster. | `elasticsearch` |
| `DESTINATION_ES_PASSWORD` | The password of the destination Elasticsearch cluster. | `changeme` |
| `DESTINATION_ES_INDEX_NAME` | The name of the destination Elasticsearch index. By default, the index name is `opengatellm`, corresponds to the default index name in the configuration file. | `opengatellm` |
| `DESTINATION_ES_VECTOR_SIZE` | The vector size corresponds to the dimension of the vector embedding used by the embeddings model setup in your configuration file (ex: `1024`). | `1024` |
| `DESTINATION_ES_NUMBER_OF_SHARDS` | The number of shards of the destination Elasticsearch index, check Elasticsearch documentation to know the maximum number of shards per node. | `1` |
| `DESTINATION_ES_NUMBER_OF_REPLICAS` | The number of replicas of the destination Elasticsearch index, check Elasticsearch documentation to know the maximum number of replicas per node. | `1` |
| `DESTINATION_ES_INDEX_LANGUAGE` | The language of the destination Elasticsearch index. The supported languages are: `french`, `english`, `german`, `italian`, `portuguese`, `spanish`, `swedish`. | `french` |

4. Run the script

1. Without nohup:

    ```bash
    ./run.sh
    ```

2. With nohup to run the script in the background:

    ```bash
    nohup ./run.sh > migration.log 2>&1 &
    ```

In both cases, the script will output the progress of the migration to the `migration.log` file. If script fails, you can rerun it, it will continue from the last point where it failed.

5. Check the migration

```bash
cat migration.log
````

## Revision History

| Date | Author | Changes |
| --- | --- | --- |
| 2026-01-30 | Development Team | Initial ADR |