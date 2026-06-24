#!/bin/bash
set -euo pipefail

VAULTFILE=".vault"

command -v ansible-vault >/dev/null 2>&1 || {
  echo >&2 "ansible-vault must be installed."
  exit 1
}

while [[ "${1:-}" == --* ]]; do
  case $1 in
    --vault-password-file)
      VAULTFILE="$2"
      shift 2
      ;;
    --vault-password-file=*)
      VAULTFILE=${1#*=}
      shift 1
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

is_vault_encrypted() {
  head -1 "$1" | grep -q '^\$ANSIBLE_VAULT;'
}

for f in "$@"; do
  if is_vault_encrypted "$f"; then
    ansible-vault view --vault-password-file "$VAULTFILE" "$f" > /dev/null
  else
    ansible-vault encrypt --vault-password-file "$VAULTFILE" "$f"
    echo "Encrypted $f — re-stage the file before committing."
  fi
done
