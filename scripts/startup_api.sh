#!/bin/bash
set -e

# Environment variables
SERVER=${SERVER:-"gunicorn"}
SERVER_CMD_ARGS=${SERVER_CMD_ARGS:-""} # ex: --log-config app/log.conf

WORKERS=${WORKERS:-1}
WORKER_CONNECTIONS=${WORKER_CONNECTIONS:-1000}
TIMEOUT=${TIMEOUT:-30}
KEEP_ALIVE=${KEEP_ALIVE:-75}
GRACEFUL_TIMEOUT=${GRACEFUL_TIMEOUT:-75}
PYTHON_VENV_PATH=${PYTHON_VENV_PATH:-""}

if [ ! -z "$PYTHON_VENV_PATH" ]; then
  source "$PYTHON_VENV_PATH/bin/activate"
fi

# Set default hosts if not already defined
if [ -z "$POSTGRES_HOST" ]; then
  export POSTGRES_HOST=localhost
fi
if [ -z "$REDIS_HOST" ]; then
  export REDIS_HOST=localhost
fi
if [ -z "$QDRANT_HOST" ]; then
  export QDRANT_HOST=localhost
fi

# Run database migrations
python -m alembic -c api/alembic.ini upgrade head

# Start the application server
if [[ $SERVER == "gunicorn" ]]; then
  exec gunicorn api.main:app \
      --workers $WORKERS \
      --worker-connections $WORKER_CONNECTIONS \
      --timeout $TIMEOUT \
      --worker-class uvicorn.workers.UvicornWorker \
      --keep-alive $KEEP_ALIVE \
      --graceful-timeout $GRACEFUL_TIMEOUT \
      --bind 0.0.0.0:8000 \
      $SERVER_CMD_ARGS  

elif [[ $SERVER == "uvicorn" ]]; then
  # Start the application server
  exec uvicorn api.main:app \
      --host 0.0.0.0 \
      --port 8000 \
      --workers $WORKERS \
      $SERVER_CMD_ARGS
else
  echo "Invalid server: $SERVER (only gunicorn and uvicorn are supported)"
  exit 1
fi
