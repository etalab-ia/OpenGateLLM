# ADR - 2026-01-30 - Elasticsearch Scaling

**Status:** In Progress
**Date:** 2026-01-30
**Authors:** Development Team
**Decision Outcome:** Merge Elasticsearch indices into a single index

---

## Context

[WIP]

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

```bash
./run.sh
```

The script will output the progress of the migration to the `migration.log` file. If script fails, you can rerun it, it will continue from the last point where it failed.

5. Check the migration

```bash
cat migration.log