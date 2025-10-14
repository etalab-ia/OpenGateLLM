#!/bin/bash
set -e

# Environment variables
SERVER=${SERVER:-"gunicorn"}
SERVER_CMD_ARGS=${SERVER_CMD_ARGS:-""} # ex: --log-config app/log.conf

# Run database migrations
python -m alembic -c api/alembic.ini upgrade head

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
