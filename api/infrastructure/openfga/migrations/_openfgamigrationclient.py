from openfga_sdk import ClientConfiguration
from openfga_sdk.client import OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple
from openfga_sdk.credentials import CredentialConfiguration, Credentials

_TIMEOUT_MILLISEC = 30_000


class OpenFgaMigrationError(RuntimeError):
    pass


class OpenFgaMigrationClient:
    def __init__(self, url: str, api_token: str, store_name: str) -> None:
        self.store_name = store_name
        self._client = OpenFgaClient(
            configuration=ClientConfiguration(
                api_url=url.rstrip("/"),
                credentials=Credentials(method="api_token", configuration=CredentialConfiguration(api_token=api_token)),
                timeout_millisec=_TIMEOUT_MILLISEC,
            )
        )

    async def connect(self) -> tuple[str, str]:
        store_id = await self._resolve_store_id()
        self._client.set_store_id(store_id)

        authorization_model_id = await self._resolve_latest_authorization_model_id()
        self._client.set_authorization_model_id(authorization_model_id)

        return store_id, authorization_model_id

    async def _resolve_store_id(self) -> str:
        matches: list[str] = []
        continuation_token = ""
        while True:
            options = {"name": self.store_name}
            if continuation_token:
                options["continuation_token"] = continuation_token
            page = await self._client.list_stores(options=options)
            matches += [store.id for store in page.stores if store.name == self.store_name]
            continuation_token = page.continuation_token or ""
            if not continuation_token:
                break

        if not matches:
            raise OpenFgaMigrationError(f"no OpenFGA store named {self.store_name!r}")
        if len(matches) > 1:
            raise OpenFgaMigrationError(f"{len(matches)} OpenFGA stores are named {self.store_name!r} ({', '.join(matches)}), refusing to guess")

        return matches[0]

    async def _resolve_latest_authorization_model_id(self) -> str:
        latest = await self._client.read_latest_authorization_model()
        if latest.authorization_model is None:
            raise OpenFgaMigrationError(f"store {self.store_name!r} holds no authorization model")

        return latest.authorization_model.id

    async def aclose(self) -> None:
        await self._client.close()

    async def check(self, subject: str, relation: str, object_: str) -> bool:
        request = ClientCheckRequest(user=subject, relation=relation, object=object_)
        response = await self._client.check(body=request)

        return response.allowed

    async def write(self, subject: str, relation: str, object_: str) -> None:
        relation_tuple = ClientTuple(user=subject, relation=relation, object=object_)
        await self._client.write_tuples(body=[relation_tuple])
