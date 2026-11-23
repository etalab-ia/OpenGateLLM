#!/bin/bash
set -eo pipefail

read_openfga_config() {
    local key_path=".dependencies.openfga.$1"
    local key_is_missing
    key_is_missing=$(yq "$key_path == null" "$CONFIG_FILE") || exit 1
    if [ "$key_is_missing" = true ]; then
        echo "${key_path#.} is missing from $CONFIG_FILE (see config.example.yml)." >&2
        exit 1
    fi
    yq "$key_path | envsubst(nu,ne)" "$CONFIG_FILE"
}

url=$(read_openfga_config url)
api_token=$(read_openfga_config api_token)
store_name=$(read_openfga_config store_name)
fga_options=(--api-url "$url" --api-token "$api_token")

echo "Looking up OpenFGA store '$store_name' at $url..."
stores=$(fga store list "${fga_options[@]}" --name "$store_name")
case $(jq '.stores | length' <<< "$stores") in
    0)
        echo "OpenFGA store '$store_name' not found, creating it..."
        store_id=$(fga store create "${fga_options[@]}" --name "$store_name" | jq -r '.store.id')
        echo "OpenFGA store '$store_name' created ($store_id)."
        ;;
    1)
        store_id=$(jq -r '.stores[0].id' <<< "$stores")
        echo "OpenFGA store '$store_name' found ($store_id)."
        ;;
    *)
        echo "Several OpenFGA stores are named '$store_name' ($(jq -r '[.stores[].id] | join(" ")' <<< "$stores")), refusing to guess." >&2
        exit 1
        ;;
esac

published_model=$(fga model get "${fga_options[@]}" --store-id "$store_id" --format fga 2>/dev/null || true)
local_model=$(fga model transform --file api/infrastructure/openfga/model.fga --output-format fga)

if [ "$published_model" = "$local_model" ]; then
    echo "OpenFGA authorization model unchanged, skipping publication..."
else
    echo "OpenFGA authorization model changed, publishing new version..."
    model_id=$(fga model write "${fga_options[@]}" --store-id "$store_id" --file api/infrastructure/openfga/model.fga | jq -r '.authorization_model_id')
    echo "OpenFGA authorization model $model_id published."
fi
