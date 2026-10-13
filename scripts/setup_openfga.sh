#!/bin/bash
set -eo pipefail

: "${FGA_API_URL:?must be set to the OpenFGA API url}"
: "${FGA_API_TOKEN:?must be set to the OpenFGA pre-shared key}"
: "${FGA_STORE_NAME:?must be set to the OpenFGA store name}"

stores=$(fga store list --name "$FGA_STORE_NAME")
case $(jq '.stores | length' <<< "$stores") in
    0) FGA_STORE_ID=$(fga store create --name "$FGA_STORE_NAME" | jq -r '.store.id') ;;
    1) FGA_STORE_ID=$(jq -r '.stores[0].id' <<< "$stores") ;;
    *) echo "Several OpenFGA stores are named '$FGA_STORE_NAME' ($(jq -r '[.stores[].id] | join(" ")' <<< "$stores")), refusing to guess." >&2; exit 1 ;;
esac
export FGA_STORE_ID

published_model=$(fga model get --format fga 2>/dev/null || true)
local_model=$(fga model transform --file api/infrastructure/openfga/model.fga --output-format fga)

if [ "$published_model" = "$local_model" ]; then
    echo "OpenFGA authorization model unchanged, skipping publication..."
else
    echo "OpenFGA authorization model changed, publishing new version..."
    model_id=$(fga model write --file api/infrastructure/openfga/model.fga | jq -r '.authorization_model_id')
    echo "OpenFGA authorization model $model_id published."
fi
