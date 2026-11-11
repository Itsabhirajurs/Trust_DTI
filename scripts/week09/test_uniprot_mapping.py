
import json
import time

import pandas as pd
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

BASE = "https://rest.uniprot.org"

INPUT = "data/interim/uniprot_human_sequences.parquet"

# Retry transient GET failures, but never automatically
# repeat job submissions.
retry = Retry(
    total=4,
    connect=4,
    read=4,
    status=4,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET"]),
    respect_retry_after_header=True,
)

session = requests.Session()

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry),
)

session.headers.update({
    "User-Agent": "TrustDTI-Research/1.0"
})


# --------------------------------------------------
# 2. Load 10 valid protein identifiers
# --------------------------------------------------

sequences = pd.read_parquet(
    INPUT,
    columns=["accession"]
)

accessions = sorted(
    sequences["accession"]
    .dropna()
    .astype(str)
    .unique()
)[:10]

print("Testing accessions:", accessions)


# --------------------------------------------------
# 3. Submit one small job
# --------------------------------------------------

response = session.post(
    f"{BASE}/idmapping/run",
    data={
        "from": "UniProtKB_AC-ID",
        "to": "Ensembl",
        "ids": ",".join(accessions),
    },
    timeout=30,
)

response.raise_for_status()

job_id = response.json().get("jobId")

if not job_id:
    raise RuntimeError(
        f"No job ID returned: {response.text}"
    )

print("\nJob submitted:", job_id)


# --------------------------------------------------
# 4. Poll job status
# --------------------------------------------------

status_url = (
    f"{BASE}/idmapping/status/{job_id}"
)

finished = False

for attempt in range(1, 41):

    response = session.get(
        status_url,
        timeout=30,
    )

    try:
        status = response.json()

    except ValueError:
        raise RuntimeError(
            f"Invalid status response: {response.text[:1000]}"
        )

    print(
        f"Attempt {attempt}: HTTP {response.status_code}",
        status,
    )

    if status.get("jobStatus") == "ERROR":

        raise RuntimeError(
            "UniProt processing failed.\n"
            + json.dumps(status, indent=2)
        )

    if response.status_code >= 400:

        raise RuntimeError(
            f"HTTP {response.status_code}: "
            f"{response.text[:1500]}"
        )

    if (
        status.get("jobStatus") == "FINISHED"
        or "results" in status
        or "failedIds" in status
    ):

        finished = True
        break

    time.sleep(3)


if not finished:

    raise TimeoutError(
        f"Job did not finish. Job ID: {job_id}"
    )


# --------------------------------------------------
# 5. Retrieve results
# --------------------------------------------------

print("\nJOB FINISHED. Downloading results.")

result = session.get(
    f"{BASE}/idmapping/stream/{job_id}",
    params={"format": "tsv"},
    timeout=60,
)

result.raise_for_status()

print("\nMAPPING RESULTS")
print(result.text[:5000])

print("\nTEST SUCCESSFUL.")
