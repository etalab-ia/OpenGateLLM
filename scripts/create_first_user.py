import argparse

import requests

parser = argparse.ArgumentParser()
parser.add_argument("--api_url", type=str, default="http://localhost:8000")
parser.add_argument("--master_key", type=str, default="changeme")
parser.add_argument("--first_email", type=str, default="my-first-user")
parser.add_argument("--first_password", type=str, default="changeme")


if __name__ == "__main__":
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.master_key}"}

    #  Get models list
    response = requests.get(f"{args.api_url}/v1/admin/routers", headers=headers)
    assert response.status_code == 200, response.text
    routers = response.json()["data"]

    # Create a new admin role
    limits = []
    for router in routers:
        limits.append({"router": router["id"], "type": "rpm", "value": None})
        limits.append({"router": router["id"], "type": "rpd", "value": None})
        limits.append({"router": router["id"], "type": "tpm", "value": None})
        limits.append({"router": router["id"], "type": "tpd", "value": None})

    response = requests.post(
        url=f"{args.api_url}/v1/admin/roles",
        headers=headers,
        json={"name": "my-first-role", "permissions": ["admin"], "limits": limits},
    )
    assert response.status_code == 201, response.text
    role_id = response.json()["id"]

    # Create a new admin user
    response = requests.post(
        url=f"{args.api_url}/v1/admin/users",
        headers=headers,
        json={"email": args.first_email, "name": args.first_email, "password": args.first_password, "role": role_id},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    # Create a new token for the admin user
    response = requests.post(url=f"{args.api_url}/v1/admin/tokens", headers=headers, json={"user": user_id, "name": "my-first-token"})
    assert response.status_code == 201, response.text

    key = response.json()["token"]

    print(f"""
New user created:
- Email: {args.first_email}
- Password: {args.first_password}
- API key: {key}
""")
