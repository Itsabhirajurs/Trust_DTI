
import requests

JOB_ID = "49GfcdqYkg"

BASE_URL = "https://rest.uniprot.org/idmapping"

ENDPOINTS = [
    "status",
    "details",
    "results",
    "stream",
]

print("=" * 65)
print("UNIPROT JOB DIAGNOSTICS")
print("=" * 65)

for endpoint in ENDPOINTS:

    url = f"{BASE_URL}/{endpoint}/{JOB_ID}"

    try:

        response = requests.get(
            url,
            timeout=30,
            allow_redirects=False,
        )

        print("\n" + "-" * 60)
        print("ENDPOINT:", endpoint)
        print("HTTP STATUS:", response.status_code)
        print("REQUEST URL:", response.url)
        print(
            "REDIRECT LOCATION:",
            response.headers.get("Location")
        )
        print("RESPONSE BODY:")
        print(response.text[:1500])

    except requests.RequestException as error:

        print("\nENDPOINT:", endpoint)
        print("REQUEST ERROR:", str(error))

print("\nDIAGNOSTICS COMPLETE.")
