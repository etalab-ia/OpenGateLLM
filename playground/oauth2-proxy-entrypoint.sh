#!/bin/sh
set -eu

if [ -z "${OAUTH2_PROXY_CLIENT_ID:-}" ]; then
  echo "oauth2-proxy: OAUTH2_PROXY_CLIENT_ID not set, skipping"
  exit 0
fi

exec /usr/local/bin/oauth2-proxy --config /playground/oauth2-proxy.cfg
