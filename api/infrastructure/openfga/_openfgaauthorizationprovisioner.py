import json
import logging
from pathlib import Path

from openfga_sdk.client import ClientConfiguration, OpenFgaClient
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from openfga_sdk.models.create_store_request import CreateStoreRequest
from openfga_sdk.models.write_authorization_model_request import WriteAuthorizationModelRequest

logger = logging.getLogger(__name__)


class AuthorizationModelNotProvisionedError(RuntimeError):
    pass


class OpenFgaAuthorizationProvisioner:
    AUTHORIZATION_MODEL_PATH = Path(__file__).parent / "model.json"

    def __init__(self, url: str, store_name: str, api_token: str):
        self.store_name = store_name
        self.client_configuration = ClientConfiguration(
            api_url=url,
            credentials=Credentials(method="api_token", configuration=CredentialConfiguration(api_token=api_token)),
        )

    async def provision(self) -> str:
        client = self._client()
        try:
            store_id = await self._resolve_store_id(client=client)
            if store_id is None:
                store_id = (await client.create_store(body=CreateStoreRequest(name=self.store_name))).id
                logger.info("OpenFGA store created.", extra={"store_name": self.store_name, "store_id": store_id})

            client.set_store_id(store_id)

            model = json.loads(self.AUTHORIZATION_MODEL_PATH.read_text())
            print(model)
            request = WriteAuthorizationModelRequest(type_definitions=model["type_definitions"], schema_version=model["schema_version"], conditions=model.get("conditions", {}))  # fmt: off
            authorization_model_id = (await client.write_authorization_model(body=request)).authorization_model_id

            logger.info("OpenFGA authorization model written.", extra={"store_id": store_id, "authorization_model_id": authorization_model_id})  # fmt: off

            return authorization_model_id
        finally:
            await client.close()

    async def connect(self) -> OpenFgaClient:
        client = self._client()

        store_id = await self._resolve_store_id(client=client)
        if store_id is None:
            await client.close()
            raise AuthorizationModelNotProvisionedError(f"OpenFGA store '{self.store_name}' does not exist. Run scripts/provision_openfga.py first.")  # fmt: off

        client.set_store_id(store_id)

        latest = await client.read_latest_authorization_model()
        if latest is None or latest.authorization_model is None:
            await client.close()
            raise AuthorizationModelNotProvisionedError(f"OpenFGA store '{self.store_name}' has no authorization model. Run scripts/provision_openfga.py first.")  # fmt: off

        client.set_authorization_model_id(latest.authorization_model.id)

        return client

    def _client(self) -> OpenFgaClient:
        return OpenFgaClient(configuration=self.client_configuration)

    async def _resolve_store_id(self, client: OpenFgaClient) -> str | None:
        stores = await client.list_stores()
        store = next((store for store in stores.stores if store.name == self.store_name), None)

        return None if store is None else store.id
