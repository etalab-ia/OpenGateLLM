import ovh
import os
import sys

# 🔐 Load credentials from environment variables
APP_KEY = os.getenv("OVH_APP_KEY")
APP_SECRET = os.getenv("OVH_APP_SECRET")
CONSUMER_KEY = os.getenv("OVH_CONSUMER_KEY")

# 📌 DNS parameters
DOMAIN = "etalab.gouv.fr"
CNAME_SUBDOMAIN = "docs.opengatellm"
CNAME_TARGET = "etalab-ia.github.io."
TXT_SUBDOMAIN = "_github-pages-challenge-etalab-ia.docs.opengatellm"
TXT_TARGET = '"fadc7d567d241d7ddbbf351cba47d4"'


def get_client():
    return ovh.Client(
        endpoint="ovh-eu",
        application_key=APP_KEY,
        application_secret=APP_SECRET,
        consumer_key=CONSUMER_KEY,
    )


def find_record(client, domain, subdomain, record_type):
    try:
        return client.get(f"/domain/zone/{domain}/record", fieldType=record_type, subDomain=subdomain)
    except ovh.exceptions.APIError as e:
        print(f"❌ Error fetching {record_type} records for {subdomain}: {e}")
        return []


def get_record_details(client, domain, record_id):
    return client.get(f"/domain/zone/{domain}/record/{record_id}")


def update_or_create_record(client, domain, subdomain, record_type, expected_value):
    records = find_record(client, domain, subdomain, record_type)

    for record_id in records:
        record = get_record_details(client, domain, record_id)
        if record["target"] == expected_value:
            print(f"✅ {record_type} record for {subdomain} is valid: {expected_value}")
            return
        else:
            print(f"⚠️ Updating invalid {record_type} record for {subdomain} (found: {record['target']})")
            client.put(f"/domain/zone/{domain}/record/{record_id}", target=expected_value)
            client.post(f"/domain/zone/{domain}/refresh")
            return

    print(f"➕ Creating new {record_type} record for {subdomain}")
    client.post(f"/domain/zone/{domain}/record", fieldType=record_type, subDomain=subdomain, target=expected_value, ttl=60)
    client.post(f"/domain/zone/{domain}/refresh")


def main():
    if not all([APP_KEY, APP_SECRET, CONSUMER_KEY]):
        print("❌ Missing OVH credentials in environment variables.")
        sys.exit(1)

    client = get_client()

    update_or_create_record(client, DOMAIN, CNAME_SUBDOMAIN, "CNAME", CNAME_TARGET)
    update_or_create_record(client, DOMAIN, TXT_SUBDOMAIN, "TXT", TXT_TARGET)


if __name__ == "__main__":
    main()
