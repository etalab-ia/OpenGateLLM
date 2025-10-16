#!/bin/bash
set -e

CELERY_EXTRA_ARGS=${CELERY_EXTRA_ARGS:-""} # ex: --loglevel INFO

exec celery --app api.tasks.celery_app.celery_app worker $CELERY_EXTRA_ARGS