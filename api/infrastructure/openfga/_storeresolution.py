from openfga_sdk.client import OpenFgaClient


async def resolve_store_id(client: OpenFgaClient, store_name: str) -> str | None:
    matches: list[str] = []
    continuation_token = ""

    while True:
        page = await client.list_stores(options={"continuation_token": continuation_token} if continuation_token else None)
        matches += [store.id for store in page.stores if store.name == store_name]
        continuation_token = page.continuation_token or ""
        if not continuation_token:
            break

    if len(matches) > 1:
        raise RuntimeError(f"{len(matches)} OpenFGA stores are named {store_name!r} ({', '.join(matches)}), refusing to guess")

    return matches[0] if matches else None
