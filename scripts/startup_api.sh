#!/bin/bash
set -e

# Prometheus
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*

# Alembic
python -m alembic -c api/alembic.ini upgrade head

# OpenFGA
python -m scripts.openfga_config

published_model=$(mktemp)
local_model=$(mktemp)

fga model get --format fga > "$published_model" 2>/dev/null || true
fga model transform --file api/infrastructure/openfga/model.fga --output-format fga > "$local_model"

if diff -q "$published_model" "$local_model" > /dev/null 2>&1; then
    echo "OpenFGA authorization model unchanged, skipping publication..."
else
    echo "OpenFGA authorization model changed, publishing new version..."
    fga model write --file api/infrastructure/openfga/model.fga
    echo "OpenFGA authorization model published successfully."
fi

rm -f "$published_model" "$local_model"

# Gunicorn
GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf
exec gunicorn api.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --config scripts/gunicorn.conf.py $GUNICORN_CMD_ARGS
