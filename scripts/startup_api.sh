#!/bin/bash
set -e

GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf

mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
# Empty prometheus dir if it exists, to prevent ghost metrics being ingested twice in case of docker restart
rm -rf "${PROMETHEUS_MULTIPROC_DIR:?}"/*

python -m alembic -c api/alembic.ini upgrade head

exec gunicorn api.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --config scripts/gunicorn.conf.py $GUNICORN_CMD_ARGS
