
"""
TrustDTI Week 09: UniProt-to-Ensembl identifier mapping.

Input:
    data/processed/network1_v1.parquet
    data/interim/uniprot_human_sequences.parquet

Method:
    UniProt asynchronous ID Mapping REST API.

Outputs:
    outputs/week09_network2/
        uniprot_ensembl_raw.tsv
        uniprot_ensembl_gene_candidates.csv
        uniprot_ensembl_accession_coverage.csv
        unmapped_uniprot_accessions.csv
        multi_mapped_uniprot_accessions.csv
        uniprot_ensembl_mapping_audit.json
        uniprot_mapping_job_history.json

The script does not modify input datasets or GitHub files.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from io import StringIO

import json
import re
import time

import pandas as pd
import requests

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

NETWORK1_PATH = (
    ROOT / "data" / "processed" / "network1_v1.parquet"
)

SEQUENCE_PATH = (
    ROOT / "data" / "interim"
    / "uniprot_human_sequences.parquet"
)

OUTPUT_DIR = (
    ROOT / "outputs" / "week09_network2"
)

API_BASE = "https://rest.uniprot.org"

SOURCE_DATABASE = "UniProtKB_AC-ID"
TARGET_DATABASE = "Ensembl"

TIMEOUT_SECONDS = 60

MAX_POLL_ATTEMPTS = 120
POLL_INTERVAL_SECONDS = 3

# Allow one controlled resubmission after a transient
# upstream service failure.
MAX_JOB_ATTEMPTS = 2

JOB_RETRY_DELAY_SECONDS = 10

# Ensembl stable gene IDs can optionally have a version.
ENSEMBL_GENE_PATTERN = re.compile(
    r"^(ENSG\d{11})(?:\.(\d+))?$"
)


# ============================================================
# 2. OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

JOB_HISTORY_PATH = (
    OUTPUT_DIR / "uniprot_mapping_job_history.json"
)


# ============================================================
# 3. HTTP SESSION WITH SAFE GET RETRIES
# ============================================================

retry_strategy = Retry(
    total=5,
    connect=5,
    read=5,
    status=5,
    backoff_factor=1,
    status_forcelist=[
        429,
        500,
        502,
        503,
        504,
    ],
    allowed_methods=frozenset(["GET"]),
    respect_retry_after_header=True,
)

session = requests.Session()

session.mount(
    "https://",
    HTTPAdapter(max_retries=retry_strategy),
)

session.headers.update({
    "User-Agent": "TrustDTI-Research/1.0",
    "Accept": "*/*",
})


# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def clean_accessions(series: pd.Series) -> pd.Series:
    """Normalize UniProt accession strings."""

    return (
        series.astype("string")
        .str.strip()
        .str.upper()
    )


def save_job_history(job_history: list[dict]) -> None:
    """Save submitted job IDs and their outcomes."""

    with JOB_HISTORY_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            job_history,
            handle,
            indent=2,
        )


def response_json(
    response: requests.Response,
    description: str,
) -> dict:
    """Parse an API response as JSON with useful error output."""

    try:

        payload = response.json()

    except ValueError as error:

        raise RuntimeError(
            f"{description}: API returned invalid JSON.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {response.text[:2000]}"
        ) from error

    if not isinstance(payload, dict):

        raise RuntimeError(
            f"{description}: Expected a JSON object."
        )

    return payload


def is_transient_job_error(payload: dict) -> bool:
    """
    Detect known transient upstream failures.

    Example encountered during this project:
        UniProt jobStatus ERROR
        Embedded error code 50
        503 Service Unavailable
    """

    error_text = json.dumps(
        payload,
        ensure_ascii=False,
    ).lower()

    transient_indicators = [
        "503 service unavailable",
        "502 bad gateway",
        "504 gateway timeout",
        '"code": 50',
        '"code":50',
    ]

    return any(
        indicator in error_text
        for indicator in transient_indicators
    )


class TransientUniProtJobError(RuntimeError):
    """A UniProt job failed due to a transient upstream error."""


# ============================================================
# 5. LOAD AND VALIDATE INPUT IDENTIFIERS
# ============================================================

def load_and_validate_inputs() -> list[str]:

    print("\n" + "=" * 65)
    print("INPUT VALIDATION")
    print("=" * 65)

    for path in [
        NETWORK1_PATH,
        SEQUENCE_PATH,
    ]:

        if not path.exists():
            raise FileNotFoundError(path)

    network = pd.read_parquet(
        NETWORK1_PATH,
        columns=["accession"],
    )

    sequences = pd.read_parquet(
        SEQUENCE_PATH,
        columns=[
            "accession",
            "is_human",
            "length_matches",
            "valid_amino_acids",
        ],
    )

    network_ids = set(
        clean_accessions(
            network["accession"]
        ).dropna().tolist()
    )

    sequence_ids = set(
        clean_accessions(
            sequences["accession"]
        ).dropna().tolist()
    )

    missing_sequences = network_ids - sequence_ids

    extra_sequences = sequence_ids - network_ids

    print(
        "Network 1 unique accessions:",
        len(network_ids),
    )

    print(
        "Sequence table unique accessions:",
        len(sequence_ids),
    )

    print(
        "Missing sequence-table accessions:",
        len(missing_sequences),
    )

    print(
        "Extra sequence-table accessions:",
        len(extra_sequences),
    )

    if missing_sequences or extra_sequences:

        raise ValueError(
            "Network 1 and sequence-table identifier sets differ."
        )

    sequences["accession_clean"] = clean_accessions(
        sequences["accession"]
    )

    if sequences["accession_clean"].duplicated().any():

        raise ValueError(
            "Duplicate accessions found in sequence table."
        )

    validation_columns = [
        "is_human",
        "length_matches",
        "valid_amino_acids",
    ]

    for column in validation_columns:

        passed = int(
            sequences[column]
            .fillna(False)
            .sum()
        )

        print(
            f"{column}: {passed}/{len(sequences)}"
        )

        if not sequences[column].fillna(False).all():

            raise ValueError(
                f"Sequence validation failed for {column}."
            )

    accessions = sorted(network_ids)

    if not accessions:

        raise ValueError(
            "No valid protein accessions found."
        )

    if len(accessions) > 100000:

        raise ValueError(
            "Input exceeds the documented 100,000-ID "
            "limit for one UniProt mapping job."
        )

    print("\nAll input checks passed.")

    return accessions


# ============================================================
# 6. SUBMIT UNIPROT JOB
# ============================================================

def submit_mapping_job(
    accessions: list[str],
) -> str:

    submit_url = (
        f"{API_BASE}/idmapping/run"
    )

    response = session.post(
        submit_url,
        data={
            "from": SOURCE_DATABASE,
            "to": TARGET_DATABASE,
            "ids": ",".join(accessions),
        },
        timeout=TIMEOUT_SECONDS,
    )

    if not response.ok:

        raise RuntimeError(
            "UniProt mapping submission failed.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {response.text[:2000]}"
        )

    payload = response_json(
        response,
        "Mapping submission",
    )

    job_id = payload.get("jobId")

    if not job_id:

        raise RuntimeError(
            "UniProt did not return a job ID.\n"
            f"Response: {payload}"
        )

    return str(job_id)


# ============================================================
# 7. POLL UNIPROT JOB STATUS
# ============================================================

def wait_for_job(
    job_id: str,
) -> dict:

    status_url = (
        f"{API_BASE}/idmapping/status/{job_id}"
    )

    print("\nWaiting for UniProt job:", job_id)

    for attempt in range(
        1,
        MAX_POLL_ATTEMPTS + 1,
    ):

        response = session.get(
            status_url,
            timeout=TIMEOUT_SECONDS,
        )

        payload = response_json(
            response,
            "UniProt job status",
        )

        job_status = payload.get("jobStatus")

        # Process the API's explicit job error first,
        # because failed jobs can return HTTP 400.
        if job_status in ["ERROR", "FAILED"]:

            message = (
                "UniProt job returned an error:\n"
                + json.dumps(payload, indent=2)
            )

            if is_transient_job_error(payload):

                raise TransientUniProtJobError(
                    message
                )

            raise RuntimeError(message)

        if response.status_code >= 400:

            raise RuntimeError(
                f"UniProt status request failed: "
                f"HTTP {response.status_code}\n"
                f"{response.text[:2000]}"
            )

        # UniProt can return results directly in the
        # status response when a job has completed.
        if (
            job_status == "FINISHED"
            or "results" in payload
            or "failedIds" in payload
        ):

            print(
                "Job completed successfully.",
                f"(poll attempt {attempt})",
            )

            return payload

        if attempt % 10 == 0:

            print(
                f"Still processing... "
                f"{attempt}/{MAX_POLL_ATTEMPTS}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        "UniProt mapping job exceeded the polling window.\n"
        f"Job ID: {job_id}"
    )


# ============================================================
# 8. SUBMIT AND RECOVER THE FULL MAPPING JOB
# ============================================================

def run_mapping_job(
    accessions: list[str],
) -> tuple[str, dict, list[dict]]:

    history = []

    for job_attempt in range(
        1,
        MAX_JOB_ATTEMPTS + 1,
    ):

        print("\n" + "=" * 65)

        print(
            f"UNIPROT JOB ATTEMPT "
            f"{job_attempt}/{MAX_JOB_ATTEMPTS}"
        )

        print("=" * 65)

        job_id = submit_mapping_job(
            accessions
        )

        record = {
            "attempt": job_attempt,
            "job_id": job_id,
            "submitted_at_utc": (
                datetime.now(timezone.utc).isoformat()
            ),
            "status": "SUBMITTED",
        }

        history.append(record)

        save_job_history(history)

        print("Job submitted successfully.")
        print("Job ID:", job_id)

        try:

            status_payload = wait_for_job(
                job_id
            )

            record["status"] = "COMPLETED"

            record["completed_at_utc"] = (
                datetime.now(timezone.utc).isoformat()
            )

            save_job_history(history)

            return (
                job_id,
                status_payload,
                history,
            )

        except TransientUniProtJobError as error:

            record["status"] = "TRANSIENT_ERROR"

            record["error"] = str(error)

            save_job_history(history)

            print("\nTransient UniProt service error.")

            print(str(error)[:2500])

            if job_attempt >= MAX_JOB_ATTEMPTS:

                raise RuntimeError(
                    "Maximum UniProt job attempts reached. "
                    "Check the saved job history before retrying."
                ) from error

            print(
                f"\nRetrying once after "
                f"{JOB_RETRY_DELAY_SECONDS} seconds..."
            )

            time.sleep(JOB_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        "Mapping job could not be completed."
    )


# ============================================================
# 9. DOWNLOAD ALL RESULTS
# ============================================================

def download_mapping_results(
    job_id: str,
) -> pd.DataFrame:

    print("\n" + "=" * 65)
    print("DOWNLOADING MAPPING RESULTS")
    print("=" * 65)

    stream_url = (
        f"{API_BASE}/idmapping/stream/{job_id}"
    )

    response = session.get(
        stream_url,
        params={"format": "tsv"},
        timeout=120,
    )

    # Fallback to the paginated results endpoint
    # in case the stream endpoint is temporarily unavailable.
    if not response.ok:

        print(
            "Stream request failed:",
            response.status_code,
        )

        print(
            "Attempting results endpoint..."
        )

        results_url = (
            f"{API_BASE}/idmapping/results/{job_id}"
        )

        response = session.get(
            results_url,
            params={"format": "tsv"},
            timeout=120,
        )

    if not response.ok:

        raise RuntimeError(
            "Unable to download UniProt mapping results.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {response.text[:2000]}"
        )

    if not response.text.strip():

        raise RuntimeError(
            "UniProt returned an empty mapping result."
        )

    raw_mapping = pd.read_csv(
        StringIO(response.text),
        sep="\t",
        dtype="string",
    )

    if raw_mapping.empty:

        raise RuntimeError(
            "The returned mapping table is empty."
        )

    print(
        "Raw mapping rows:",
        len(raw_mapping),
    )

    print(
        "Returned columns:",
        raw_mapping.columns.tolist(),
    )

    return raw_mapping


# ============================================================
# 10. EXTRACT AND VALIDATE ENSEMBL GENE IDS
# ============================================================

def process_mapping(
    raw_mapping: pd.DataFrame,
    accessions: list[str],
):

    column_lookup = {
        column.strip().lstrip("\ufeff").lower(): column
        for column in raw_mapping.columns
    }

    if (
        "from" not in column_lookup
        or "to" not in column_lookup
    ):

        raise ValueError(
            "Unexpected UniProt TSV format.\n"
            f"Columns: {raw_mapping.columns.tolist()}"
        )

    from_column = column_lookup["from"]
    to_column = column_lookup["to"]

    mapping = raw_mapping[
        [from_column, to_column]
    ].copy()

    mapping.columns = [
        "uniprot_accession",
        "mapped_identifier",
    ]

    mapping["uniprot_accession"] = clean_accessions(
        mapping["uniprot_accession"]
    )

    mapping["mapped_identifier"] = (
        mapping["mapped_identifier"]
        .astype("string")
        .str.strip()
    )

    mapping = mapping.dropna(
        subset=[
            "uniprot_accession",
            "mapped_identifier",
        ]
    )

    unexpected_accessions = (
        set(mapping["uniprot_accession"])
        - set(accessions)
    )

    if unexpected_accessions:

        raise ValueError(
            "UniProt returned unexpected source accessions: "
            f"{sorted(unexpected_accessions)[:10]}"
        )

    # Preserve versioned Ensembl IDs while extracting
    # the stable identifier and numeric version.
    parsed = mapping["mapped_identifier"].str.extract(
        ENSEMBL_GENE_PATTERN
    )

    mapping["ensembl_gene_id"] = parsed[0]

    mapping["ensembl_version"] = parsed[1]

    mapping["is_ensembl_gene"] = (
        mapping["ensembl_gene_id"].notna()
    )

    gene_mapping = mapping.loc[
        mapping["is_ensembl_gene"],
        [
            "uniprot_accession",
            "mapped_identifier",
            "ensembl_gene_id",
            "ensembl_version",
        ],
    ].copy()

    gene_mapping = gene_mapping.rename(
        columns={
            "mapped_identifier":
                "ensembl_gene_id_versioned"
        }
    )

    # Retain version information and avoid duplicate
    # identical mapping rows.
    gene_mapping = gene_mapping.drop_duplicates(
        subset=[
            "uniprot_accession",
            "ensembl_gene_id_versioned",
        ]
    )

    return mapping, gene_mapping


# ============================================================
# 11. BUILD PER-ACCESSION COVERAGE
# ============================================================

def build_coverage(
    gene_mapping: pd.DataFrame,
    accessions: list[str],
):

    stable_counts = (
        gene_mapping.groupby("uniprot_accession")
        ["ensembl_gene_id"]
        .nunique()
    )

    versioned_counts = (
        gene_mapping.groupby("uniprot_accession")
        ["ensembl_gene_id_versioned"]
        .nunique()
    )

    coverage = pd.DataFrame({
        "uniprot_accession": accessions
    })

    coverage["ensembl_gene_count"] = (
        coverage["uniprot_accession"]
        .map(stable_counts)
        .fillna(0)
        .astype(int)
    )

    coverage["versioned_mapping_count"] = (
        coverage["uniprot_accession"]
        .map(versioned_counts)
        .fillna(0)
        .astype(int)
    )

    coverage["mapping_status"] = coverage[
        "ensembl_gene_count"
    ].map(
        lambda count:
            "NO_MAPPING"
            if count == 0
            else "ONE_TO_ONE"
            if count == 1
            else "ONE_TO_MANY"
    )

    return coverage


# ============================================================
# 12. SAVE OUTPUTS AND AUDIT REPORT
# ============================================================

def save_outputs(
    job_id: str,
    history: list[dict],
    raw_mapping: pd.DataFrame,
    mapping: pd.DataFrame,
    gene_mapping: pd.DataFrame,
    coverage: pd.DataFrame,
    accessions: list[str],
):

    raw_output = (
        OUTPUT_DIR / "uniprot_ensembl_raw.tsv"
    )

    gene_output = (
        OUTPUT_DIR / "uniprot_ensembl_gene_candidates.csv"
    )

    coverage_output = (
        OUTPUT_DIR / "uniprot_ensembl_accession_coverage.csv"
    )

    unmapped_output = (
        OUTPUT_DIR / "unmapped_uniprot_accessions.csv"
    )

    multi_output = (
        OUTPUT_DIR / "multi_mapped_uniprot_accessions.csv"
    )

    audit_output = (
        OUTPUT_DIR / "uniprot_ensembl_mapping_audit.json"
    )

    # Save all original returned mapping records.
    raw_mapping.to_csv(
        raw_output,
        sep="\t",
        index=False,
    )

    # Save Ensembl gene candidates.
    gene_mapping.to_csv(
        gene_output,
        index=False,
    )

    # Save every input accession with its mapping status.
    coverage.to_csv(
        coverage_output,
        index=False,
    )

    # Save accessions without an Ensembl gene mapping.
    unmapped = coverage.loc[
        coverage["mapping_status"].eq("NO_MAPPING")
    ]

    unmapped.to_csv(
        unmapped_output,
        index=False,
    )

    # Save one-to-many mappings for manual review.
    multi_mapped = coverage.loc[
        coverage["mapping_status"].eq("ONE_TO_MANY")
    ]

    multi_mapped.to_csv(
        multi_output,
        index=False,
    )

    mapped_accessions = set(
        gene_mapping["uniprot_accession"]
    )

    mapping_status_counts = (
        coverage["mapping_status"]
        .value_counts()
        .to_dict()
    )

    audit = {

        "project": "TrustDTI",

        "task": "UniProt to Ensembl mapping",

        "retrieved_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),

        "api": API_BASE,

        "source_database": SOURCE_DATABASE,

        "target_database": TARGET_DATABASE,

        "job_id": job_id,

        "job_history": history,

        "input_network1_accessions": len(accessions),

        "raw_mapping_rows": len(raw_mapping),

        "unique_raw_mapping_pairs": len(mapping),

        "ensembl_gene_mapping_rows": len(gene_mapping),

        "unique_uniprot_gene_pairs": (
            gene_mapping[
                [
                    "uniprot_accession",
                    "ensembl_gene_id",
                ]
            ].drop_duplicates().shape[0]
        ),

        "accessions_with_gene_mapping": len(
            mapped_accessions
        ),

        "accessions_without_gene_mapping": (
            len(accessions) - len(mapped_accessions)
        ),

        "one_to_one_accessions": int(
            mapping_status_counts.get(
                "ONE_TO_ONE", 0
            )
        ),

        "one_to_many_accessions": int(
            mapping_status_counts.get(
                "ONE_TO_MANY", 0
            )
        ),

        "unmapped_accessions": int(
            mapping_status_counts.get(
                "NO_MAPPING", 0
            )
        ),

        "distinct_ensembl_gene_ids": int(
            gene_mapping["ensembl_gene_id"].nunique()
        ),

        "mapping_coverage_percentage": round(
            len(mapped_accessions)
            / len(accessions)
            * 100,
            4,
        ),

        "mapping_status_distribution": {
            str(key): int(value)
            for key, value in mapping_status_counts.items()
        },

        "outputs": {
            "raw_mapping": str(raw_output),
            "gene_candidates": str(gene_output),
            "accession_coverage": str(coverage_output),
            "unmapped_accessions": str(unmapped_output),
            "multi_mapped_accessions": str(multi_output),
            "job_history": str(JOB_HISTORY_PATH),
        },

    }

    with audit_output.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            audit,
            handle,
            indent=2,
        )

    return audit


# ============================================================
# 13. MAIN WORKFLOW
# ============================================================

def main():

    print("\n" + "=" * 70)
    print("TRUSTDTI: FULL UNIPROT-TO-ENSEMBL MAPPING")
    print("=" * 70)

    # Step 1: Validate the local inputs.
    accessions = load_and_validate_inputs()

    print(
        "\nTotal identifiers to submit:",
        len(accessions),
    )

    # Step 2: Submit and poll the asynchronous job.
    job_id, status_payload, history = run_mapping_job(
        accessions
    )

    print(
        "\nFinal job status response:",
        json.dumps(
            status_payload,
            indent=2,
        )[:3000],
    )

    # Step 3: Download all mapping results.
    raw_mapping = download_mapping_results(
        job_id
    )

    # Step 4: Extract stable and versioned Ensembl IDs.
    mapping, gene_mapping = process_mapping(
        raw_mapping,
        accessions,
    )

    # Step 5: Quantify mapping coverage.
    coverage = build_coverage(
        gene_mapping,
        accessions,
    )

    # Step 6: Save everything.
    audit = save_outputs(
        job_id,
        history,
        raw_mapping,
        mapping,
        gene_mapping,
        coverage,
        accessions,
    )

    # Step 7: Print final results.
    print("\n" + "=" * 70)
    print("FINAL UNIPROT-ENSEMBL MAPPING AUDIT")
    print("=" * 70)

    print(
        json.dumps(
            audit,
            indent=2,
        )
    )

    print("\nMAPPING STATUS DISTRIBUTION")

    print(
        coverage["mapping_status"]
        .value_counts()
        .to_string()
    )

    print("\nFIRST 15 ENSEMBL GENE MAPPINGS")

    print(
        gene_mapping.head(15).to_string(index=False)
    )

    print("\nUNMAPPED ACCESSIONS")

    print(
        coverage.loc[
            coverage["mapping_status"].eq("NO_MAPPING")
        ].head(15).to_string(index=False)
    )

    print("\nMULTI-MAPPED ACCESSIONS")

    print(
        coverage.loc[
            coverage["mapping_status"].eq("ONE_TO_MANY")
        ].head(15).to_string(index=False)
    )

    print("\nOUTPUT DIRECTORY:")
    print(OUTPUT_DIR)

    print("\nMAPPING AUDIT COMPLETED SUCCESSFULLY.")


# ============================================================
# 14. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nExecution interrupted. "
            "Check the saved job history before resubmitting."
        )

        raise

    except Exception as error:

        print("\n" + "=" * 65)
        print("MAPPING WORKFLOW FAILED")
        print("=" * 65)

        print(type(error).__name__ + ":", str(error))

        print(
            "\nCheck:",
            JOB_HISTORY_PATH,
        )

        raise
