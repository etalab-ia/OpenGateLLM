#!/bin/sh
set -eu

ALPHA_CONFIG=/playground/oauth2-proxy-alpha.yaml

if [ ! -f "$ALPHA_CONFIG" ]; then
  echo "oauth2-proxy: alpha config not present, skipping"
  exit 0
fi

exec /usr/local/bin/oauth2-proxy --alpha-config "$ALPHA_CONFIG"
