#!/bin/bash
set -e

# Environment variables
SERVER=${SERVER:-"gunicorn"}
SERVER_CMD_ARGS=${SERVER_CMD_ARGS:-""} # ex: --log-config app/log.conf

# Run database migrations
python -m alembic -c api/alembic.ini upgrade head

# Optionally start Celery worker (single generic worker consuming all model.* queues)
# Control via env vars: CELERY_TASK_ALWAYS_EAGER=true|false, CELERY_CONCURRENCY, CELERY_EXTRA_ARGS
if [ "${CELERY_TASK_ALWAYS_EAGER:-true}" = "false" ]; then
  echo "[startup] Launching Celery worker..."
  CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-4}
  CELERY_QUEUES=${CELERY_QUEUES:-"router_*"}
  # If wildcard unsupported (e.g. Redis broker), user can pass explicit comma list via CELERY_QUEUES
  celery -A api.tasks.celery_app.celery_app worker \
    -n albert-worker@%h \
    -Q ${CELERY_QUEUES} \
    -c ${CELERY_CONCURRENCY} \
    --loglevel=${CELERY_LOG_LEVEL:-INFO} ${CELERY_EXTRA_ARGS:-""} &
fi

# Start the application server
if [[ $SERVER == "gunicorn" ]]; then
  exec gunicorn api.main:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8000 \
      $SERVER_CMD_ARGS  

elif [[ $SERVER == "uvicorn" ]]; then
  # Start the application server
  exec uvicorn api.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      $SERVER_CMD_ARGS
else
  echo "Invalid server: $SERVER (only gunicorn and uvicorn are supported)"
  exit 1
fi
