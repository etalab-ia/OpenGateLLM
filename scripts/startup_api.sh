#!/bin/bash
set -e

GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf

python -m alembic -c api/alembic.ini upgrade head

exec gunicorn api.main:app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 $GUNICORN_CMD_ARGS  
