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

    role_name = "my-first-role"
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
            if role["name"] == "my-first-role":
                role_id = role["id"]
                break
    else:
        assert response.status_code == 201, response.text
        role_id = response.json()["id"]

    # Create a new admin user
    response = requests.post(
        url=f"{args.api_url}/v1/admin/users",
        headers=headers,
        json={"email": args.first_email, "name": args.first_email, "password": args.first_password, "role": role_id},
    )
    if response.status_code == 409:
        response = requests.get(f"{args.api_url}/v1/admin/users", headers=headers)
        assert response.status_code == 200, response.text
        users = response.json()["data"]
        for user in users:
            if user["email"] == args.first_email:
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

    display_limits = "\n                   ".join([f"{router["name"]} → unlimited" for router in routers])

    print(f"""
\033[32;1m✔ {message} \033[0m

\033[32;1mRole:\033[0m              {role_name}
\033[32;1mRole permissions:\033[0m  {",".join(role_permissions)}
\033[32;1mRole limits: \033[0m      
                   {display_limits}

\033[32;1mEmail:\033[0m             {args.first_email}
\033[32;1mPassword:\033[0m          {args.first_password}

\033[32;1mAPI key:\033[0m           {key}
""")
