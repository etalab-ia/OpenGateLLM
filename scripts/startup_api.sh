#!/bin/bash
set -e

GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf

export PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus_multiproc}"
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*

python -m alembic -c api/alembic.ini upgrade head

exec gunicorn api.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --config scripts/gunicorn.conf.py $GUNICORN_CMD_ARGS
