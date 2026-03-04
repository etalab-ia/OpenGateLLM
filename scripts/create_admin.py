import argparse

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

parser = argparse.ArgumentParser()
parser.add_argument("--api_url", type=str, default="http://localhost:8000")
parser.add_argument("--master_key", type=str, default="changeme")
parser.add_argument("--email", type=str, default="admin")
parser.add_argument("--password", type=str, default="changeme")


if __name__ == "__main__":
    console = Console()
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.master_key}"}

    #  Get models list
    response = requests.get(f"{args.api_url}/v1/admin/routers", headers=headers)
    assert response.status_code == 200, response.text
    routers = response.json()["data"]

    role_name = "admin"
    role_permissions = ["admin"]
    role_limits = []

    # Create a new admin role
    for router in routers:
        role_limits.append({"router": router["id"], "type": "rpm", "value": None})
        role_limits.append({"router": router["id"], "type": "rpd", "value": None})
        role_limits.append({"router": router["id"], "type": "tpm", "value": None})
        role_limits.append({"router": router["id"], "type": "tpd", "value": None})

    response = requests.post(
        url=f"{args.api_url}/v1/admin/roles",
        headers=headers,
        json={"name": role_name, "permissions": role_permissions, "limits": role_limits},
    )
    if response.status_code == 409:
        response = requests.get(f"{args.api_url}/v1/admin/roles", headers=headers)
        assert response.status_code == 200, response.text
        roles = response.json()["data"]
        for role in roles:
            if role["name"] == role_name:
                role_id = role["id"]
                break
    else:
        assert response.status_code == 201, response.text
        role_id = response.json()["id"]

    # Create a new admin user
    response = requests.post(
        url=f"{args.api_url}/v1/admin/users",
        headers=headers,
        json={"email": args.email, "name": args.email, "password": args.password, "role": role_id},
    )
    if response.status_code == 409:
        response = requests.get(f"{args.api_url}/v1/admin/users", headers=headers)
        assert response.status_code == 200, response.text
        users = response.json()["data"]
        for user in users:
            if user["email"] == args.email:
                user_id = user["id"]
                break
        message = "User already exists, new api key created."
    else:
        message = "User created with success."
        assert response.status_code == 201, response.text
        user_id = response.json()["id"]

    # Create a new token for the admin user
    response = requests.post(url=f"{args.api_url}/v1/admin/tokens", headers=headers, json={"user": user_id, "name": "my-first-token"})
    assert response.status_code == 201, response.text

    key = response.json()["token"]

    limits_table = Table(box=box.SIMPLE_HEAD, header_style="bold cyan")
    limits_table.add_column("Router")
    limits_table.add_column("Limit")
    for router in routers:
        limits_table.add_row(router["name"], "unlimited")

    summary_table = Table(box=box.SIMPLE_HEAD, show_header=False)
    summary_table.add_column("Field", style="bold green")
    summary_table.add_column("Value", overflow="fold")
    summary_table.add_row("Role", role_name)
    summary_table.add_row("Role permissions", ",".join(role_permissions))
    summary_table.add_row("Email", args.email)
    summary_table.add_row("Password", args.password)
    summary_table.add_row("API key", key)

    console.print(f"✔ {message}", style="bold green")
    console.print()
    console.print(Panel(summary_table, title="User information", border_style="bright_blue", padding=(1, 2)))
    console.print()
    console.print(Panel(limits_table, title="Role limits", border_style="bright_blue", padding=(1, 2)))
