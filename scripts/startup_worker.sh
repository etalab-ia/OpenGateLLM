#!/bin/bash
set -e

CELERY_EXTRA_ARGS=${CELERY_EXTRA_ARGS:-""} # ex: --loglevel INFO

exec celery --app api.tasks.app worker $CELERY_EXTRA_ARGS
