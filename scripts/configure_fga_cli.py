import asyncio
from pathlib import Path
import sys

from openfga_sdk import ClientConfiguration
from openfga_sdk.client import OpenFgaClient
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from openfga_sdk.models.create_store_request import CreateStoreRequest
import yaml

from api.infrastructure.configuration import get_configuration
from api.infrastructure.openfga import resolve_store_id

CONFIG_PATH = Path.home() / ".fga.yaml"


async def main() -> None:
    openfga_config = get_configuration().dependencies.openfga
    client = OpenFgaClient(
        configuration=ClientConfiguration(
            api_url=openfga_config.url,
            credentials=Credentials(method="api_token", configuration=CredentialConfiguration(api_token=openfga_config.api_token)),
        )
    )

    try:
        store_id = await resolve_store_id(client=client, store_name=openfga_config.store_name)
        if store_id is None:
            store_id = (await client.create_store(body=CreateStoreRequest(name=openfga_config.store_name))).id
    finally:
        await client.close()

    settings = {"api-url": openfga_config.url, "api-token": openfga_config.api_token, "store-id": store_id}
    CONFIG_PATH.write_text(yaml.safe_dump(settings))
    CONFIG_PATH.chmod(0o600)

    print(f"fga CLI configured for store {openfga_config.store_name!r} ({store_id}).", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
