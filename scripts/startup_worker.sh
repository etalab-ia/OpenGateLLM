#!/bin/bash
set -e

CELERY_EXTRA_ARGS=${CELERY_EXTRA_ARGS:-""} # ex: --loglevel INFO

exec celery -A api.tasks.app worker \
    --loglevel=info \
    -Q control \
    -E \
    --max-tasks-per-child=1000 \
    -c 4 \
    --pool=prefork \
    $CELERY_EXTRA_ARGS
