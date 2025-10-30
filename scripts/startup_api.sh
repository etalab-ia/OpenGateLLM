#!/bin/bash
set -e

GUNICORN_CMD_ARGS=${GUNICORN_CMD_ARGS:-""} # ex: --log-config app/log.conf

python -m alembic -c api/alembic.ini upgrade head

# Optionally start Celery worker (single generic worker consuming all model.* queues)
# Control via env vars: CELERY_TASK_ALWAYS_EAGER=true|false, CELERY_CONCURRENCY, CELERY_EXTRA_ARGS
if [ "${CELERY_TASK_ALWAYS_EAGER:-true}" = "false" ]; then
  echo "[startup] Launching Celery worker..."
  CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-4}
  CELERY_QUEUES=${CELERY_QUEUES:-"model.*"}
  # If wildcard unsupported (e.g. Redis broker), user can pass explicit comma list via CELERY_QUEUES
  celery -A api.tasks.celery_app.celery_app worker \
    -n albert-worker@%h \
    -Q ${CELERY_QUEUES} \
    -c ${CELERY_CONCURRENCY} \
    --loglevel=${CELERY_LOG_LEVEL:-INFO} ${CELERY_EXTRA_ARGS:-""} &
fi

exec gunicorn api.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    $GUNICORN_CMD_ARGS  

