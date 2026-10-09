#!/bin/bash
set -e

# Prometheus
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*

# Alembic
python -m alembic -c api/alembic.ini upgrade head

# OpenFGA
bash scripts/setup_openfga.sh

# Gunicorn
GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf
exec gunicorn api.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --config scripts/gunicorn.conf.py $GUNICORN_CMD_ARGS
