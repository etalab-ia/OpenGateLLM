import argparse
from uuid import uuid4

import requests
from rich.console import Console

parser = argparse.ArgumentParser()
parser.add_argument("--api_url", type=str, default="http://localhost:8000")
parser.add_argument("--master_key", type=str, default="changeme")
parser.add_argument("--email", type=str, default="admin")
parser.add_argument("--password", type=str, default="changeme")
parser.add_argument("--key_name", type=str, default="my-api-key")


if __name__ == "__main__":
    console = Console()
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.master_key}"}
    # Health check
    response = requests.get(url=f"{args.api_url}/health", headers=headers)
    if response.status_code != 200:
        console.print(f"❌ API is not reachable ({args.api_url})", style="bold red")
        exit(1)

    # Login
    response = requests.post(url=f"{args.api_url}/v1/auth/login", headers=headers, json={"email": args.email, "password": args.password})
    assert response.status_code == 200, response.text
    tmp_api_key = response.json()["value"]

    # Create a new API key
    response = requests.post(
        url=f"{args.api_url}/v1/me/keys",
        headers={"Authorization": f"Bearer {tmp_api_key}"},
        json={
            "name": f"my-first-key-{uuid4()}",
        },
    )
    assert response.status_code == 201, response.text
    api_key = response.json()["key"]

    console.print(f"✔ API key created successfully for user {args.email}", style="bold green")
    console.print(api_key)
    console.print()
