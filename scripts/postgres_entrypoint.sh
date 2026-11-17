#!/bin/bash
# Run by the postgres image from /docker-entrypoint-initdb.d, only when its data directory is empty.
set -e

for database in $(echo "$CREATE_DB" | tr ',' ' '); do
    echo "Creating database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres -c "CREATE DATABASE \"$database\" WITH ENCODING 'utf8'"
done
